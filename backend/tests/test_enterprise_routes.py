"""Tests for Enterprise API Routes."""

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app

ENTERPRISE_HEADERS = {
    "X-Org-ID": "test-org",
    "X-API-Key": "enterprise-key-long-enough-12345",
}


@pytest.fixture
async def fake_redis():
    server = fakeredis.FakeServer()
    redis = fakeredis.aioredis.FakeRedis(server=server)
    yield redis
    await redis.close()


@pytest.fixture
async def client(fake_redis):
    """HTTP client with Redis dependency override."""
    app = create_app()

    # Override the Redis dep to use fake
    from app.dependencies import get_redis

    app.dependency_overrides[get_redis] = lambda: fake_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# --- Auth Tests ---


class TestEnterpriseAuth:
    @pytest.mark.asyncio
    async def test_missing_headers(self, client):
        resp = await client.get("/api/v1/enterprise/features")
        assert resp.status_code == 422  # Missing required headers

    @pytest.mark.asyncio
    async def test_short_api_key(self, client):
        resp = await client.get(
            "/api/v1/enterprise/features",
            headers={"X-Org-ID": "org", "X-API-Key": "short"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_auth(self, client):
        resp = await client.get(
            "/api/v1/enterprise/features",
            headers=ENTERPRISE_HEADERS,
        )
        assert resp.status_code == 200


# --- Features ---


class TestFeatures:
    @pytest.mark.asyncio
    async def test_get_features(self, client):
        resp = await client.get(
            "/api/v1/enterprise/features",
            headers=ENTERPRISE_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "meta" in data
        assert data["meta"]["tier"] == "enterprise"


# --- Team Endpoints ---


class TestTeamEndpoints:
    @pytest.mark.asyncio
    async def test_add_member(self, client):
        resp = await client.post(
            "/api/v1/enterprise/team/members",
            headers=ENTERPRISE_HEADERS,
            json={
                "member_hash": "abcdef1234567890",
                "scores": {
                    "activity": 80.0,
                    "collaboration": 65.0,
                },
                "archetype": "backend_architect",
                "ai_tools_detected": ["copilot"],
                "top_languages": ["Python", "Go"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["status"] == "added"
        assert data["meta"]["org_id"] == "test-org"

    @pytest.mark.asyncio
    async def test_get_empty_dashboard(self, client):
        resp = await client.get(
            "/api/v1/enterprise/team/dashboard",
            headers=ENTERPRISE_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["team_size"] == 0

    @pytest.mark.asyncio
    async def test_add_and_get_dashboard(self, client):
        # Add member
        await client.post(
            "/api/v1/enterprise/team/members",
            headers=ENTERPRISE_HEADERS,
            json={
                "member_hash": "hash12345678",
                "scores": {"activity": 90, "collaboration": 70},
                "archetype": "full_stack_polyglot",
                "ai_tools_detected": ["cursor"],
                "top_languages": ["TypeScript"],
            },
        )

        # Get dashboard
        resp = await client.get(
            "/api/v1/enterprise/team/dashboard?period=30d",
            headers=ENTERPRISE_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["team_size"] == 1
        assert data["aggregate_scores"]["activity"] == 90.0

    @pytest.mark.asyncio
    async def test_team_comparison(self, client):
        resp = await client.get(
            "/api/v1/enterprise/team/comparison",
            headers=ENTERPRISE_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "members" in data["data"]

    @pytest.mark.asyncio
    async def test_remove_member(self, client):
        resp = await client.delete(
            "/api/v1/enterprise/team/members/somehash",
            headers=ENTERPRISE_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "removed" in data["data"]

    @pytest.mark.asyncio
    async def test_invalid_period(self, client):
        resp = await client.get(
            "/api/v1/enterprise/team/dashboard?period=invalid",
            headers=ENTERPRISE_HEADERS,
        )
        assert resp.status_code == 422


# --- White-Label Endpoints ---


class TestWhiteLabelEndpoints:
    @pytest.mark.asyncio
    async def test_get_unconfigured(self, client):
        resp = await client.get(
            "/api/v1/enterprise/whitelabel",
            headers=ENTERPRISE_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["configured"] is False

    @pytest.mark.asyncio
    async def test_save_and_get_config(self, client):
        # Save
        resp = await client.put(
            "/api/v1/enterprise/whitelabel",
            headers=ENTERPRISE_HEADERS,
            json={
                "org_id": "test-org",
                "company_name": "Test Corp",
                "primary_color": "#FF0000",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "saved"

        # Get
        resp = await client.get(
            "/api/v1/enterprise/whitelabel",
            headers=ENTERPRISE_HEADERS,
        )
        data = resp.json()
        assert data["data"]["configured"] is True
        assert data["data"]["config"]["company_name"] == "Test Corp"

    @pytest.mark.asyncio
    async def test_save_wrong_org_forbidden(self, client):
        resp = await client.put(
            "/api/v1/enterprise/whitelabel",
            headers=ENTERPRISE_HEADERS,
            json={
                "org_id": "different-org",
                "company_name": "Other Corp",
            },
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_get_branding(self, client):
        resp = await client.get(
            "/api/v1/enterprise/whitelabel/branding",
            headers=ENTERPRISE_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "company_name" in data
        assert "css_variables" in data

    @pytest.mark.asyncio
    async def test_delete_config(self, client):
        resp = await client.delete(
            "/api/v1/enterprise/whitelabel",
            headers=ENTERPRISE_HEADERS,
        )
        assert resp.status_code == 200


# --- PDF Report ---


class TestPDFEndpoint:
    @pytest.mark.asyncio
    async def test_generate_pdf(self, client):
        resp = await client.post(
            "/api/v1/enterprise/report/pdf",
            headers=ENTERPRISE_HEADERS,
            json={
                "scores": {"activity": 85, "collaboration": 72},
                "archetype": {
                    "name": "Full-Stack Polyglot",
                    "description": "Multi-stack dev",
                },
                "ai_analysis": {
                    "overall_bucket": "moderate",
                    "detected_tools": ["copilot"],
                },
                "tech_profile": {
                    "languages": [{"name": "Python", "percentage": 60}],
                },
            },
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF-1.4")

    @pytest.mark.asyncio
    async def test_generate_pdf_empty_data(self, client):
        resp = await client.post(
            "/api/v1/enterprise/report/pdf",
            headers=ENTERPRISE_HEADERS,
            json={
                "scores": {},
                "archetype": {},
                "ai_analysis": {},
                "tech_profile": {},
            },
        )
        assert resp.status_code == 200
        assert len(resp.content) > 100


# --- SSO Endpoints ---


class TestSSOEndpoints:
    @pytest.mark.asyncio
    async def test_initiate_unconfigured(self, client):
        resp = await client.post(
            "/api/v1/enterprise/sso/initiate",
            json={"org_id": "no-sso-org"},
        )
        # SSO not configured → should error
        assert resp.status_code in (401, 500)

    @pytest.mark.asyncio
    async def test_validate_nonexistent_session(self, client):
        resp = await client.get(
            "/api/v1/enterprise/sso/session/nonexistent-id",
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_session(self, client):
        resp = await client.delete(
            "/api/v1/enterprise/sso/session/some-session-id",
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["revoked"] is False

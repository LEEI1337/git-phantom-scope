"""Tests for generation API endpoints."""

import json
import sys
from unittest.mock import MagicMock, patch

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def gen_client():
    """Async client with mocked Redis for generation endpoint tests."""
    app = create_app()

    # Mock Redis dependency
    server = fakeredis.FakeServer()
    fake_redis = fakeredis.aioredis.FakeRedis(server=server)

    async def mock_get_redis():
        yield fake_redis

    app.dependency_overrides = {}

    from app.dependencies import get_redis

    app.dependency_overrides[get_redis] = mock_get_redis

    # Disable rate limiting for tests
    from api.deps import rate_limit_generate

    app.dependency_overrides[rate_limit_generate] = lambda: None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, fake_redis

    await fake_redis.close()


class TestGenerateEndpoint:
    @pytest.mark.asyncio
    async def test_generate_requires_valid_session(self, gen_client):
        client, redis = gen_client

        with patch("api.v1.routes.generate.generate_profile_package") as mock_celery:
            mock_celery.delay = lambda **kwargs: None

            response = await client.post(
                "/api/v1/public/generate",
                json={
                    "session_id": "nonexistent-session",
                    "assets": ["readme"],
                },
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_with_valid_session(self, gen_client):
        client, redis = gen_client

        # Create a valid session
        session_data = json.dumps(
            {
                "scoring_result": {
                    "scores": {"activity": 50},
                    "archetype": {"name": "Developer"},
                    "tech_profile": {"languages": []},
                }
            }
        )
        await redis.setex("session:test-session-123", 1800, session_data)

        # Mock celery_worker module since celery isn't installed in test env
        mock_task = MagicMock()
        mock_task.delay = MagicMock()
        mock_celery_module = MagicMock()
        mock_celery_module.generate_profile_package = mock_task

        with patch.dict(
            sys.modules,
            {"app.celery_worker": mock_celery_module},
        ):
            response = await client.post(
                "/api/v1/public/generate",
                json={
                    "session_id": "test-session-123",
                    "assets": ["readme", "banner"],
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert data["estimated_time_seconds"] > 0

    @pytest.mark.asyncio
    async def test_job_status_not_found(self, gen_client):
        client, redis = gen_client

        response = await client.get("/api/v1/public/generate/nonexistent-job-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_job_status_returns_progress(self, gen_client):
        client, redis = gen_client

        # Create a job record in Redis
        job_data = json.dumps(
            {
                "job_id": "test-job-456",
                "status": "processing",
                "progress": 45,
            }
        )
        await redis.setex("job:test-job-456", 14400, job_data)

        response = await client.get("/api/v1/public/generate/test-job-456")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["progress"] == 45


class TestDownloadEndpoint:
    @pytest.mark.asyncio
    async def test_download_not_complete(self, gen_client):
        client, redis = gen_client

        job_data = json.dumps(
            {
                "job_id": "test-job-dl",
                "status": "processing",
                "progress": 50,
            }
        )
        await redis.setex("job:test-job-dl", 14400, job_data)

        response = await client.get("/api/v1/public/generate/test-job-dl/download")
        assert response.status_code == 500  # GenerationError

    @pytest.mark.asyncio
    async def test_download_job_not_found(self, gen_client):
        client, redis = gen_client

        response = await client.get("/api/v1/public/generate/nonexistent/download")
        assert response.status_code == 404

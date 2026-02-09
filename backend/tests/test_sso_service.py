"""Tests for SSO/SAML Authentication Service."""

import fakeredis.aioredis
import pytest
from pydantic import ValidationError

from services.sso_service import (
    SSOConfig,
    SSOError,
    SSOProvider,
    SSOService,
    SSOSession,
)


@pytest.fixture
async def fake_redis():
    server = fakeredis.FakeServer()
    redis = fakeredis.aioredis.FakeRedis(server=server)
    yield redis
    await redis.close()


@pytest.fixture
def service(fake_redis):
    return SSOService(fake_redis)


@pytest.fixture
def sample_sso_config():
    return SSOConfig(
        org_id="acme",
        provider=SSOProvider.SAML,
        entity_id="https://idp.acme.com/entity",
        sso_url="https://idp.acme.com/sso/saml",
        certificate_fingerprint="A" * 40,
        allowed_domains=["acme.com", "example.com"],
        auto_provision=True,
        default_role="member",
    )


@pytest.fixture
def oidc_config():
    return SSOConfig(
        org_id="oidc-org",
        provider=SSOProvider.OIDC,
        entity_id="client-id-123",
        sso_url="https://auth.example.com/authorize",
        certificate_fingerprint="B" * 40,
        allowed_domains=["example.com"],
    )


@pytest.fixture
def github_config():
    return SSOConfig(
        org_id="gh-org",
        provider=SSOProvider.GITHUB,
        entity_id="gh-client-id",
        sso_url="https://github.com/login/oauth/authorize",
        certificate_fingerprint="C" * 40,
    )


# --- Model Tests ---


class TestSSOConfig:
    def test_valid_config(self, sample_sso_config):
        assert sample_sso_config.org_id == "acme"
        assert sample_sso_config.provider == SSOProvider.SAML

    def test_defaults(self):
        config = SSOConfig(
            org_id="test",
            entity_id="eid",
            sso_url="https://sso.example.com",
            certificate_fingerprint="A" * 40,
        )
        assert config.provider == SSOProvider.SAML
        assert config.auto_provision is True
        assert config.default_role == "member"
        assert config.allowed_domains == []

    def test_invalid_cert_too_short(self):
        with pytest.raises(ValidationError):
            SSOConfig(
                org_id="test",
                entity_id="eid",
                sso_url="https://sso.test.com",
                certificate_fingerprint="short",
            )


class TestSSOSession:
    def test_creation(self):
        session = SSOSession(
            org_id="acme",
            provider=SSOProvider.SAML,
            user_hash="abc123",
        )
        assert session.session_id != ""
        assert session.role == "member"
        assert session.authenticated_at != ""

    def test_unique_session_ids(self):
        s1 = SSOSession(org_id="a", provider=SSOProvider.SAML, user_hash="x")
        s2 = SSOSession(org_id="a", provider=SSOProvider.SAML, user_hash="x")
        assert s1.session_id != s2.session_id


class TestSSOProvider:
    def test_values(self):
        assert SSOProvider.SAML.value == "saml"
        assert SSOProvider.OIDC.value == "oidc"
        assert SSOProvider.GITHUB.value == "github"


# --- Config Management ---


class TestSSOServiceConfig:
    @pytest.mark.asyncio
    async def test_save_and_get(self, service, sample_sso_config):
        result = await service.save_sso_config(sample_sso_config)
        assert result["status"] == "configured"
        assert result["org_id"] == "acme"

        config = await service.get_sso_config("acme")
        assert config is not None
        assert config.provider == SSOProvider.SAML
        assert config.sso_url == "https://idp.acme.com/sso/saml"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, service):
        config = await service.get_sso_config("nonexistent")
        assert config is None

    @pytest.mark.asyncio
    async def test_delete_config(self, service, sample_sso_config):
        await service.save_sso_config(sample_sso_config)
        deleted = await service.delete_sso_config("acme")
        assert deleted is True
        assert await service.get_sso_config("acme") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, service):
        deleted = await service.delete_sso_config("nonexistent")
        assert deleted is False


# --- SSO Flow ---


class TestSSOFlow:
    @pytest.mark.asyncio
    async def test_initiate_saml(self, service, sample_sso_config):
        await service.save_sso_config(sample_sso_config)
        result = await service.initiate_sso("acme")
        assert "redirect_url" in result
        assert "state" in result
        assert result["provider"] == "saml"
        assert "SAMLRequest" in result["redirect_url"]
        assert "RelayState" in result["redirect_url"]

    @pytest.mark.asyncio
    async def test_initiate_oidc(self, service, oidc_config):
        await service.save_sso_config(oidc_config)
        result = await service.initiate_sso("oidc-org")
        assert result["provider"] == "oidc"
        assert "response_type=code" in result["redirect_url"]
        assert "client_id=client-id-123" in result["redirect_url"]
        assert "nonce=" in result["redirect_url"]

    @pytest.mark.asyncio
    async def test_initiate_github(self, service, github_config):
        await service.save_sso_config(github_config)
        result = await service.initiate_sso("gh-org")
        assert result["provider"] == "github"
        assert "github.com/login/oauth/authorize" in result["redirect_url"]
        assert "client_id=gh-client-id" in result["redirect_url"]

    @pytest.mark.asyncio
    async def test_initiate_unconfigured_raises(self, service):
        with pytest.raises(SSOError, match="not configured"):
            await service.initiate_sso("nonexistent")

    @pytest.mark.asyncio
    async def test_verify_callback_success(self, service, sample_sso_config):
        await service.save_sso_config(sample_sso_config)
        init = await service.initiate_sso("acme")

        session = await service.verify_callback(
            state=init["state"],
            assertion_data={
                "subject": "user-123",
                "email": "user@acme.com",
            },
        )
        assert session.org_id == "acme"
        assert session.provider == SSOProvider.SAML
        assert session.role == "member"
        assert session.user_hash != ""
        assert session.session_id != ""

    @pytest.mark.asyncio
    async def test_verify_callback_invalid_state(self, service):
        with pytest.raises(SSOError, match="Invalid or expired"):
            await service.verify_callback(
                state="fake-state",
                assertion_data={"subject": "user"},
            )

    @pytest.mark.asyncio
    async def test_verify_callback_domain_filter(self, service, sample_sso_config):
        """acme.com allows only acme.com and example.com domains."""
        await service.save_sso_config(sample_sso_config)
        init = await service.initiate_sso("acme")

        with pytest.raises(SSOError, match="domain not authorized"):
            await service.verify_callback(
                state=init["state"],
                assertion_data={
                    "subject": "user-123",
                    "email": "user@evil.com",
                },
            )

    @pytest.mark.asyncio
    async def test_verify_callback_no_domain_restriction(self, service):
        config = SSOConfig(
            org_id="open",
            provider=SSOProvider.SAML,
            entity_id="eid",
            sso_url="https://sso.open.com",
            certificate_fingerprint="A" * 40,
            allowed_domains=[],  # no restriction
        )
        await service.save_sso_config(config)
        init = await service.initiate_sso("open")

        session = await service.verify_callback(
            state=init["state"],
            assertion_data={
                "subject": "user-xyz",
                "email": "user@anything.com",
            },
        )
        assert session.org_id == "open"

    @pytest.mark.asyncio
    async def test_nonce_one_time_use(self, service, sample_sso_config):
        """Nonce should be consumed after first verification."""
        await service.save_sso_config(sample_sso_config)
        init = await service.initiate_sso("acme")

        # First use succeeds
        await service.verify_callback(
            state=init["state"],
            assertion_data={"subject": "user", "email": "u@acme.com"},
        )

        # Second use fails (nonce consumed)
        with pytest.raises(SSOError, match="Invalid or expired"):
            await service.verify_callback(
                state=init["state"],
                assertion_data={"subject": "user", "email": "u@acme.com"},
            )


# --- Session Management ---


class TestSSOSessions:
    @pytest.mark.asyncio
    async def test_validate_session(self, service, sample_sso_config):
        await service.save_sso_config(sample_sso_config)
        init = await service.initiate_sso("acme")
        session = await service.verify_callback(
            state=init["state"],
            assertion_data={"subject": "user", "email": "u@acme.com"},
        )

        validated = await service.validate_session(session.session_id)
        assert validated is not None
        assert validated.org_id == "acme"
        assert validated.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_validate_invalid_session(self, service):
        result = await service.validate_session("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_revoke_session(self, service, sample_sso_config):
        await service.save_sso_config(sample_sso_config)
        init = await service.initiate_sso("acme")
        session = await service.verify_callback(
            state=init["state"],
            assertion_data={"subject": "user", "email": "u@acme.com"},
        )

        revoked = await service.revoke_session(session.session_id)
        assert revoked is True

        # Session should be gone
        assert await service.validate_session(session.session_id) is None

    @pytest.mark.asyncio
    async def test_revoke_nonexistent(self, service):
        revoked = await service.revoke_session("nonexistent")
        assert revoked is False

    @pytest.mark.asyncio
    async def test_revoke_all_sessions(self, service, sample_sso_config):
        await service.save_sso_config(sample_sso_config)

        # Create two sessions
        init1 = await service.initiate_sso("acme")
        s1 = await service.verify_callback(
            state=init1["state"],
            assertion_data={"subject": "user1", "email": "u1@acme.com"},
        )
        init2 = await service.initiate_sso("acme")
        s2 = await service.verify_callback(
            state=init2["state"],
            assertion_data={"subject": "user2", "email": "u2@acme.com"},
        )

        revoked = await service.revoke_all_sessions("acme")
        assert revoked == 2

        assert await service.validate_session(s1.session_id) is None
        assert await service.validate_session(s2.session_id) is None


# --- Identity Extraction ---


class TestIdentityExtraction:
    def test_extract_saml(self, service):
        identity = service._extract_identity(
            SSOProvider.SAML,
            {"subject": "user@saml.com", "email": "user@saml.com"},
        )
        assert identity["subject"] == "user@saml.com"
        assert identity["email_domain"] == "saml.com"

    def test_extract_oidc(self, service):
        identity = service._extract_identity(
            SSOProvider.OIDC,
            {"sub": "oidc-user-id", "email": "user@oidc.com"},
        )
        # 'sub' is mapped to subject
        assert identity["subject"] == "oidc-user-id"
        assert identity["email_domain"] == "oidc.com"

    def test_extract_no_email(self, service):
        identity = service._extract_identity(
            SSOProvider.GITHUB,
            {"subject": "gh-user"},
        )
        assert identity["subject"] == "gh-user"
        assert identity["email_domain"] == ""


# --- Error class ---


class TestSSOError:
    def test_defaults(self):
        err = SSOError()
        assert err.code == "SSO_ERROR"
        assert err.status_code == 401

    def test_custom_message(self):
        err = SSOError("Token expired")
        assert err.message == "Token expired"

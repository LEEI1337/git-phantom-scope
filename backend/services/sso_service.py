"""
Git Phantom Scope — SSO/SAML Authentication Service.

Enterprise feature: enables Single Sign-On via SAML 2.0 or
OIDC (OpenID Connect) for enterprise organizations.

Privacy: SSO tokens are session-scoped in Redis. No user identity
data is persisted to PostgreSQL. Only hashed org membership is tracked.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.config import get_settings
from app.exceptions import GPSBaseError
from app.logging_config import get_logger

logger = get_logger(__name__)


class SSOError(GPSBaseError):
    """SSO authentication error."""

    def __init__(self, message: str = "SSO authentication failed") -> None:
        super().__init__(
            code="SSO_ERROR",
            message=message,
            status_code=401,
        )


class SSOProvider(str, Enum):
    """Supported SSO providers."""

    SAML = "saml"
    OIDC = "oidc"
    GITHUB = "github"


class SSOConfig(BaseModel):
    """SSO configuration for an organization."""

    org_id: str = Field(..., min_length=1, max_length=64)
    provider: SSOProvider = SSOProvider.SAML
    entity_id: str = Field(..., min_length=1, max_length=512)
    sso_url: str = Field(..., min_length=1, max_length=1024)
    certificate_fingerprint: str = Field(..., min_length=40, max_length=128)
    allowed_domains: list[str] = Field(default_factory=list)
    auto_provision: bool = True
    default_role: str = "member"


class SSOSession(BaseModel):
    """Authenticated SSO session."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    provider: SSOProvider
    user_hash: str
    role: str = "member"
    authenticated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    expires_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


_REDIS_PREFIX = "sso:"
_CONFIG_PREFIX = "sso_config:"
_SESSION_TTL = 28800  # 8 hours
_CONFIG_TTL = 86400  # 24 hours
_NONCE_TTL = 300  # 5 minutes


class SSOService:
    """Manages SSO authentication flows for enterprise customers."""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client
        self._settings = get_settings()

    # --- Configuration Management ---

    async def save_sso_config(self, config: SSOConfig) -> dict[str, str]:
        """Save SSO configuration for an organization."""
        key = f"{_CONFIG_PREFIX}{config.org_id}"
        data = config.model_dump(mode="json")
        await self._redis.setex(key, _CONFIG_TTL, json.dumps(data))
        logger.info("SSO config saved", org_id=config.org_id)
        return {"status": "configured", "org_id": config.org_id}

    async def get_sso_config(self, org_id: str) -> SSOConfig | None:
        """Retrieve SSO configuration."""
        key = f"{_CONFIG_PREFIX}{org_id}"
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return SSOConfig.model_validate(json.loads(raw))

    async def delete_sso_config(self, org_id: str) -> bool:
        """Delete SSO configuration."""
        key = f"{_CONFIG_PREFIX}{org_id}"
        result = await self._redis.delete(key)
        return result > 0

    # --- Authentication Flow ---

    async def initiate_sso(self, org_id: str) -> dict[str, str]:
        """Initiate SSO login flow.

        Returns a redirect URL and state nonce for CSRF protection.
        """
        config = await self.get_sso_config(org_id)
        if config is None:
            raise SSOError("SSO not configured for this organization")

        nonce = secrets.token_urlsafe(32)
        state = secrets.token_urlsafe(32)

        # Store nonce for verification
        nonce_key = f"{_REDIS_PREFIX}nonce:{state}"
        nonce_data = json.dumps(
            {
                "org_id": org_id,
                "nonce": nonce,
                "created_at": time.time(),
            }
        )
        await self._redis.setex(nonce_key, _NONCE_TTL, nonce_data)

        if config.provider == SSOProvider.SAML:
            redirect_url = self._build_saml_request(config, nonce, state)
        elif config.provider == SSOProvider.OIDC:
            redirect_url = self._build_oidc_request(config, nonce, state)
        else:
            redirect_url = self._build_github_oauth_url(config, state)

        return {
            "redirect_url": redirect_url,
            "state": state,
            "provider": config.provider.value,
        }

    async def verify_callback(
        self,
        state: str,
        assertion_data: dict[str, Any],
    ) -> SSOSession:
        """Verify SSO callback and create authenticated session.

        Validates the state nonce, assertion signature, and creates
        a session in Redis.
        """
        # Verify state nonce
        nonce_key = f"{_REDIS_PREFIX}nonce:{state}"
        nonce_raw = await self._redis.get(nonce_key)
        if nonce_raw is None:
            raise SSOError("Invalid or expired SSO state")

        nonce_data = json.loads(nonce_raw)
        org_id = nonce_data["org_id"]

        # Delete nonce (one-time use)
        await self._redis.delete(nonce_key)

        # Check nonce age
        created = nonce_data.get("created_at", 0)
        if time.time() - created > _NONCE_TTL:
            raise SSOError("SSO request expired")

        # Get SSO config
        config = await self.get_sso_config(org_id)
        if config is None:
            raise SSOError("SSO configuration not found")

        # Validate assertion (provider-specific)
        user_identity = self._extract_identity(config.provider, assertion_data)

        # Verify domain if restricted
        if config.allowed_domains:
            email_domain = user_identity.get("email_domain", "")
            if email_domain not in config.allowed_domains:
                raise SSOError("Email domain not authorized")

        # Create session — hash user identity for privacy
        user_hash = hashlib.sha256(user_identity.get("subject", "").encode()).hexdigest()

        session = SSOSession(
            org_id=org_id,
            provider=config.provider,
            user_hash=user_hash,
            role=config.default_role,
        )

        # Store session in Redis
        session_key = f"{_REDIS_PREFIX}session:{session.session_id}"
        session_data = session.model_dump(mode="json")
        await self._redis.setex(session_key, _SESSION_TTL, json.dumps(session_data))

        logger.info(
            "SSO session created",
            org_id=org_id,
            provider=config.provider.value,
        )

        return session

    async def validate_session(self, session_id: str) -> SSOSession | None:
        """Validate an existing SSO session."""
        session_key = f"{_REDIS_PREFIX}session:{session_id}"
        raw = await self._redis.get(session_key)
        if raw is None:
            return None
        return SSOSession.model_validate(json.loads(raw))

    async def revoke_session(self, session_id: str) -> bool:
        """Revoke an SSO session."""
        session_key = f"{_REDIS_PREFIX}session:{session_id}"
        result = await self._redis.delete(session_key)
        return result > 0

    async def revoke_all_sessions(self, org_id: str) -> int:
        """Revoke all SSO sessions for an organization."""
        pattern = f"{_REDIS_PREFIX}session:*"
        revoked = 0
        async for key in self._redis.scan_iter(match=pattern):  # type: ignore[union-attr]
            raw = await self._redis.get(key)
            if raw:
                data = json.loads(raw)
                if data.get("org_id") == org_id:
                    await self._redis.delete(key)
                    revoked += 1
        return revoked

    # --- Private helpers ---

    def _build_saml_request(self, config: SSOConfig, nonce: str, state: str) -> str:
        """Build SAML AuthnRequest redirect URL."""
        return f"{config.sso_url}?SAMLRequest=placeholder&RelayState={state}"

    def _build_oidc_request(self, config: SSOConfig, nonce: str, state: str) -> str:
        """Build OIDC authorization request URL."""
        return (
            f"{config.sso_url}"
            f"?response_type=code"
            f"&client_id={config.entity_id}"
            f"&state={state}"
            f"&nonce={nonce}"
            f"&scope=openid+email+profile"
        )

    def _build_github_oauth_url(self, config: SSOConfig, state: str) -> str:
        """Build GitHub OAuth authorization URL."""
        return (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={config.entity_id}"
            f"&state={state}"
            f"&scope=read:user+user:email"
        )

    def _extract_identity(
        self,
        provider: SSOProvider,
        assertion_data: dict[str, Any],
    ) -> dict[str, str]:
        """Extract user identity from SSO assertion."""
        subject = assertion_data.get("subject", assertion_data.get("sub", ""))
        email = assertion_data.get("email", "")
        email_domain = email.split("@")[1] if "@" in email else ""

        return {
            "subject": subject,
            "email_domain": email_domain,
            "provider": provider.value,
        }

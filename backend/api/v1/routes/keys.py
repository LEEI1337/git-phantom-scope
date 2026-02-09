"""BYOK key validation endpoint.

POST /api/v1/keys/validate - Validate a BYOK API key
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.deps import rate_limit_by_ip
from app.logging_config import get_logger
from services.model_connector import get_connector

logger = get_logger(__name__)
router = APIRouter()


class ValidateKeyRequest(BaseModel):
    """BYOK key validation request."""

    provider: str = Field(
        ..., pattern=r"^(gemini|openai|anthropic)$",
        description="AI provider name"
    )
    api_key: str = Field(
        ..., min_length=10, max_length=500,
        description="Encrypted API key"
    )


class ValidateKeyResponse(BaseModel):
    """BYOK key validation response."""

    valid: bool
    tier: str | None = None
    rate_limits: dict | None = None
    features: dict | None = None


@router.post("/keys/validate", response_model=ValidateKeyResponse)
async def validate_byok_key(
    request: ValidateKeyRequest,
    _rate_limit: None = Depends(rate_limit_by_ip),
) -> ValidateKeyResponse:
    """Validate a BYOK API key.

    Tests the key against the provider's API to verify it works.
    The key is used only for this validation call and is NOT stored.

    SECURITY: The key exists in memory only during this request.
    """
    connector = get_connector(request.provider)

    try:
        result = await connector.validate_key(request.api_key)
        logger.info("byok_key_validated", provider=request.provider, valid=True)
        return ValidateKeyResponse(
            valid=result["valid"],
            tier=result.get("tier"),
            rate_limits=result.get("rate_limits"),
            features=result.get("features"),
        )
    except Exception:
        logger.info("byok_key_validation_failed", provider=request.provider)
        return ValidateKeyResponse(valid=False)

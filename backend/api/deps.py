"""Shared API dependencies.

Provides rate limiting, authentication, and common validation
as injectable FastAPI dependencies.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, Request
from pydantic import BaseModel, Field

import redis.asyncio as aioredis
from app.dependencies import (
    analyze_rate_limiter,
    api_rate_limiter,
    generate_rate_limiter,
    get_redis,
)
from app.logging_config import get_logger

logger = get_logger(__name__)


async def rate_limit_by_ip(
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
) -> None:
    """Apply per-IP rate limiting for API calls."""
    client_ip = request.client.host if request.client else "unknown"
    # Anonymize IP for rate limiting (use hash)
    import hashlib
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]
    await api_rate_limiter.check(ip_hash, redis)


async def rate_limit_analyze(
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
) -> None:
    """Apply per-IP rate limiting for analyze endpoint (3/day)."""
    client_ip = request.client.host if request.client else "unknown"
    import hashlib
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]
    await analyze_rate_limiter.check(ip_hash, redis)


async def rate_limit_generate(
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
) -> None:
    """Apply per-IP rate limiting for generate endpoint (5/day)."""
    client_ip = request.client.host if request.client else "unknown"
    import hashlib
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]
    await generate_rate_limiter.check(ip_hash, redis)


def get_byok_key(
    x_encrypted_key: Optional[str] = Header(None),
) -> Optional[str]:
    """Extract encrypted BYOK key from request header.

    The key is passed encrypted and will be decrypted in-memory
    only during the model API call.
    """
    return x_encrypted_key

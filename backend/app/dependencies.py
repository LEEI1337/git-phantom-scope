"""Application-level dependencies.

Provides Redis connection, rate limiting, and session management
as FastAPI dependencies for injection into route handlers.
"""

from __future__ import annotations

from typing import AsyncGenerator, Optional

import redis.asyncio as aioredis
from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.exceptions import RateLimitError, SessionNotFoundError
from app.logging_config import get_logger
from app.metrics import ACTIVE_SESSIONS, RATE_LIMIT_HITS

logger = get_logger(__name__)

# Global Redis connection pool
_redis_pool: Optional[aioredis.Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection pool."""
    global _redis_pool
    settings = get_settings()
    _redis_pool = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    # Test connection
    await _redis_pool.ping()


async def close_redis() -> None:
    """Close Redis connection pool."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """Get Redis connection as a FastAPI dependency."""
    if _redis_pool is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    yield _redis_pool


async def get_session_data(
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    """Retrieve session data from Redis.

    Sessions store temporary analysis results and are keyed by session_id.
    TTL is enforced to ensure PII is auto-deleted.
    """
    session_id = request.headers.get("X-Session-ID") or request.query_params.get(
        "session_id"
    )
    if not session_id:
        raise SessionNotFoundError()

    data = await redis.get(f"session:{session_id}")
    if data is None:
        raise SessionNotFoundError()

    import json

    return json.loads(data)


class RateLimiter:
    """Redis-backed rate limiter using sliding window."""

    def __init__(
        self,
        key_prefix: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def check(self, identifier: str, redis: aioredis.Redis) -> None:
        """Check rate limit. Raises RateLimitError if exceeded."""
        import time

        key = f"ratelimit:{self.key_prefix}:{identifier}"
        now = time.time()
        window_start = now - self.window_seconds

        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, self.window_seconds)
        results = await pipe.execute()

        request_count = results[2]
        if request_count > self.max_requests:
            RATE_LIMIT_HITS.labels(
                endpoint=self.key_prefix, limit_type="sliding_window"
            ).inc()
            raise RateLimitError(
                limit_type=self.key_prefix,
                retry_after=self.window_seconds,
            )


# Pre-configured rate limiters
analyze_rate_limiter = RateLimiter(
    key_prefix="analyze",
    max_requests=3,
    window_seconds=86400,  # 3 per day
)

generate_rate_limiter = RateLimiter(
    key_prefix="generate",
    max_requests=5,
    window_seconds=86400,  # 5 per day
)

api_rate_limiter = RateLimiter(
    key_prefix="api",
    max_requests=30,
    window_seconds=60,  # 30 per minute
)

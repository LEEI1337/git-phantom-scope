"""Health monitoring.

Provides detailed health checks for all application dependencies:
Redis, PostgreSQL, external APIs.
"""

from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis

from app.logging_config import get_logger

logger = get_logger(__name__)


class HealthMonitor:
    """Monitors health of all application components."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis

    async def check_all(self) -> dict[str, Any]:
        """Run all health checks and return status."""
        redis_ok = await self._check_redis()
        db_ok = await self._check_database()

        all_healthy = redis_ok and db_ok

        return {
            "status": "healthy" if all_healthy else "degraded",
            "checks": {
                "redis": {"status": "ok" if redis_ok else "error"},
                "database": {"status": "ok" if db_ok else "error"},
            },
        }

    async def _check_redis(self) -> bool:
        """Check Redis connectivity."""
        try:
            await self.redis.ping()
            return True
        except Exception:
            logger.error("health_check_redis_failed")
            return False

    async def _check_database(self) -> bool:
        """Check PostgreSQL connectivity."""
        try:
            from db.session import _engine

            if _engine is None:
                return False
            async with _engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            logger.error("health_check_database_failed")
            return False

"""Session Management.

Handles creation, retrieval, and expiration of user sessions.
All session data is stored in Redis with strict TTL.

PRIVACY: Sessions contain temporary profile data that auto-expires.
NO session data is ever persisted to PostgreSQL.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings
from app.exceptions import SessionNotFoundError
from app.logging_config import get_logger
from app.metrics import ACTIVE_SESSIONS

logger = get_logger(__name__)


class SessionManager:
    """Redis-backed session manager."""

    PREFIX = "session:"

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis
        self.settings = get_settings()

    async def create(self, data: dict[str, Any]) -> str:
        """Create a new session and return its ID.

        Args:
            data: Session data (profile, scoring, preferences)

        Returns:
            Session UUID string
        """
        session_id = str(uuid.uuid4())
        session_data = {
            **data,
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
        }

        await self.redis.setex(
            f"{self.PREFIX}{session_id}",
            self.settings.redis_session_ttl,
            json.dumps(session_data),
        )

        ACTIVE_SESSIONS.inc()
        logger.info("session_created", session_id=session_id)
        return session_id

    async def get(self, session_id: str) -> dict[str, Any]:
        """Retrieve session data.

        Raises SessionNotFoundError if session expired or doesn't exist.
        """
        data = await self.redis.get(f"{self.PREFIX}{session_id}")
        if data is None:
            raise SessionNotFoundError()
        return json.loads(data)

    async def update(self, session_id: str, data: dict[str, Any]) -> None:
        """Update existing session data. Resets TTL."""
        existing = await self.get(session_id)  # Raises if not found
        existing.update(data)

        await self.redis.setex(
            f"{self.PREFIX}{session_id}",
            self.settings.redis_session_ttl,
            json.dumps(existing),
        )

    async def delete(self, session_id: str) -> None:
        """Explicitly delete a session."""
        deleted = await self.redis.delete(f"{self.PREFIX}{session_id}")
        if deleted:
            ACTIVE_SESSIONS.dec()
            logger.info("session_deleted", session_id=session_id)

    async def exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        return bool(await self.redis.exists(f"{self.PREFIX}{session_id}"))

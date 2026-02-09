"""Async SQLAlchemy session management.

PostgreSQL is used ONLY for anonymous, aggregated analytics.
NO PII (usernames, emails, profile data) is ever stored here.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    """Initialize the async database engine and session factory."""
    global _engine, _session_factory
    settings = get_settings()

    _engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        echo=settings.debug,
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info("database_engine_initialized")


async def close_db() -> None:
    """Close the database engine."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("database_engine_closed")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session as a FastAPI dependency."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

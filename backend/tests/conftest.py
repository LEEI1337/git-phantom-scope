"""Shared test fixtures for Git Phantom Scope backend."""

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import fakeredis.aioredis
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Provide test settings with safe defaults."""
    return Settings(
        GPS_ENVIRONMENT="testing",
        GPS_DEBUG=True,
        GPS_DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/gps_test",
        GPS_REDIS_URL="redis://localhost:6379/15",
        GPS_GITHUB_TOKEN="ghp_test_token_fake_value",
        GPS_SECRET_KEY="test-secret-key-minimum-32-chars-long!!",
        GPS_CORS_ORIGINS="http://localhost:3000",
    )


@pytest.fixture
async def fake_redis() -> AsyncGenerator:
    """Provide a fake Redis instance for testing."""
    server = fakeredis.FakeServer()
    redis = fakeredis.aioredis.FakeRedis(server=server)
    yield redis
    await redis.aclose()


@pytest.fixture
async def app(test_settings):
    """Create a test application instance."""
    application = create_app()
    yield application


@pytest.fixture
async def client(app) -> AsyncGenerator:
    """Provide an async HTTP client for API testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_github_service():
    """Provide a mocked GitHub service."""
    service = AsyncMock()
    service.fetch_profile.return_value = {
        "login": "testuser",
        "public_repos": 42,
        "followers": 100,
        "following": 50,
        "created_at": "2020-01-01T00:00:00Z",
    }
    service.fetch_repos.return_value = [
        {
            "name": "test-repo",
            "language": "Python",
            "stargazers_count": 10,
            "forks_count": 3,
            "topics": ["python", "api"],
        },
    ]
    service.fetch_events.return_value = [
        {"type": "PushEvent", "created_at": "2025-08-01T12:00:00Z"},
        {"type": "PullRequestEvent", "created_at": "2025-08-02T12:00:00Z"},
    ]
    return service

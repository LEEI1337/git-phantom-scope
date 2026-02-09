"""Shared test fixtures for Git Phantom Scope backend."""

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from app.config import Environment, Settings
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
        environment=Environment.TESTING,
        debug=True,
        database_url="postgresql+asyncpg://test:test@localhost:5432/gps_test",
        redis_url="redis://localhost:6379/15",
        github_token=SecretStr("ghp_test_token_fake_value"),
        session_secret_key=SecretStr("test-secret-key-minimum-32-chars-long!!"),
        cors_origins=["http://localhost:3000"],
    )


@pytest.fixture
async def fake_redis() -> AsyncGenerator:
    """Provide a fake Redis instance for testing."""
    server = fakeredis.FakeServer()
    redis = fakeredis.aioredis.FakeRedis(server=server)
    yield redis
    await redis.close()


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
    service.get_profile.return_value = {
        "username": "testuser",
        "name": "Test User",
        "avatar_url": "https://example.com/avatar.png",
        "public_repos": 42,
        "followers": 100,
        "following": 50,
        "created_at": "2020-01-01T00:00:00Z",
        "bio": "Developer",
        "repos": [
            {
                "name": "test-repo",
                "language": "Python",
                "stargazers_count": 10,
                "forks_count": 3,
                "fork": False,
                "topics": ["python", "api"],
                "updated_at": "2026-01-15T12:00:00Z",
            },
        ],
        "events": [
            {"type": "PushEvent", "created_at": "2025-08-01T12:00:00Z"},
            {"type": "PullRequestEvent", "created_at": "2025-08-02T12:00:00Z"},
        ],
        "languages": {"Python": 80.0},
        "total_stars": 10,
        "total_forks": 3,
        "topics": ["python", "api"],
        "pinned_repos": [],
        "organizations": [],
        "contribution_calendar": [],
    }
    service.get_commit_history.return_value = [
        {"message": "feat: add feature", "author_login": "testuser"},
    ]
    service.invalidate_cache.return_value = 0
    return service

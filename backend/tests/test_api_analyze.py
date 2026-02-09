"""Tests for the analysis API endpoint."""

import pytest
from unittest.mock import patch, AsyncMock

import fakeredis.aioredis

from app.dependencies import get_redis
from app.exceptions import GitHubUserNotFoundError
from app.main import create_app


@pytest.fixture
async def api_client():
    """Create an async HTTP client with fake Redis dependency override."""
    from httpx import ASGITransport, AsyncClient

    app = create_app()
    server = fakeredis.FakeServer()
    fake_redis = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)

    async def override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await fake_redis.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestAnalyzeEndpoint:
    """Test suite for POST /api/v1/public/analyze."""

    def _build_mock_service(self):
        """Build a mock GitHubService with valid profile response."""
        mock = AsyncMock()
        mock.get_profile.return_value = {
            "username": "testuser",
            "name": "Test User",
            "avatar_url": "https://example.com/avatar.png",
            "bio": "Developer",
            "company": None,
            "location": None,
            "blog": None,
            "is_hireable": False,
            "public_repos": 20,
            "followers": 50,
            "following": 30,
            "created_at": "2021-01-01T00:00:00Z",
            "repos": [
                {
                    "name": "repo",
                    "language": "Python",
                    "stargazers_count": 5,
                    "stars": 5,
                    "forks_count": 2,
                    "fork": False,
                    "is_fork": False,
                    "topics": ["python"],
                    "updated_at": "2026-01-15T12:00:00Z",
                },
            ],
            "events": [
                {"type": "PushEvent", "created_at": "2025-08-10T12:00:00Z"},
            ],
            "languages": {"Python": 100.0},
            "total_stars": 5,
            "total_forks": 2,
            "topics": ["python"],
            "pinned_repos": [],
            "organizations": [],
            "contribution_calendar": [],
            "contribution_stats": {},
        }
        mock.get_commit_history.return_value = [
            {"message": "feat: add feature", "author_login": "testuser"},
        ]
        return mock

    async def test_analyze_valid_username(self, api_client):
        """Valid username returns 200 with scores and archetype."""
        mock_github = self._build_mock_service()

        with patch(
            "api.v1.routes.analyze.GitHubService",
            return_value=mock_github,
        ):
            response = await api_client.post(
                "/api/v1/public/analyze",
                json={"github_username": "testuser"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "scores" in data
        assert "archetype" in data
        assert all(
            dim in data["scores"]
            for dim in ["activity", "collaboration", "stack_diversity", "ai_savviness"]
        )
        assert data["profile"]["username"] == "testuser"
        assert "session_id" in data
        assert "meta" in data

    async def test_analyze_empty_username(self, api_client):
        """Empty username returns 422 validation error."""
        response = await api_client.post(
            "/api/v1/public/analyze",
            json={"github_username": ""},
        )
        assert response.status_code == 422

    async def test_analyze_invalid_username_chars(self, api_client):
        """Username with invalid characters returns 422."""
        response = await api_client.post(
            "/api/v1/public/analyze",
            json={"github_username": "user@invalid!"},
        )
        assert response.status_code == 422

    async def test_analyze_user_not_found(self, api_client):
        """Non-existent GitHub user returns 404."""
        mock_github = AsyncMock()
        mock_github.get_profile.side_effect = GitHubUserNotFoundError()

        with patch(
            "api.v1.routes.analyze.GitHubService",
            return_value=mock_github,
        ):
            response = await api_client.post(
                "/api/v1/public/analyze",
                json={"github_username": "nonexistentuser12345"},
            )

        assert response.status_code == 404

    async def test_analyze_response_structure(self, api_client):
        """Response contains all required fields."""
        mock_github = self._build_mock_service()

        with patch(
            "api.v1.routes.analyze.GitHubService",
            return_value=mock_github,
        ):
            response = await api_client.post(
                "/api/v1/public/analyze",
                json={"github_username": "testuser"},
            )

        assert response.status_code == 200
        data = response.json()
        for field in [
            "session_id", "profile", "scores", "archetype",
            "ai_analysis", "tech_profile", "contribution_calendar",
            "pinned_repos", "organizations", "meta",
        ]:
            assert field in data, f"Missing field: {field}"

"""Tests for the analysis API endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
class TestAnalyzeEndpoint:
    """Test suite for POST /api/v1/public/analyze."""

    async def test_analyze_valid_username(self, client):
        """Valid username returns 200 with scores and archetype."""
        mock_github = AsyncMock()
        mock_github.fetch_profile.return_value = {
            "login": "testuser",
            "public_repos": 20,
            "followers": 50,
            "following": 30,
            "created_at": "2021-01-01T00:00:00Z",
        }
        mock_github.fetch_repos.return_value = [
            {"name": "repo", "language": "Python", "stargazers_count": 5, "forks_count": 2},
        ]
        mock_github.fetch_events.return_value = [
            {"type": "PushEvent", "created_at": "2025-08-10T12:00:00Z"},
        ]

        with patch("api.v1.routes.analyze.get_github_service", return_value=mock_github):
            response = await client.post(
                "/api/v1/public/analyze",
                json={"github_username": "testuser"},
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "scores" in data
        assert "archetype" in data
        assert all(
            dim in data["scores"]
            for dim in ["activity", "collaboration", "stack_diversity", "ai_savviness"]
        )

    async def test_analyze_empty_username(self, client):
        """Empty username returns 422 validation error."""
        response = await client.post(
            "/api/v1/public/analyze",
            json={"github_username": ""},
        )
        assert response.status_code == 422

    async def test_analyze_invalid_username_chars(self, client):
        """Username with invalid characters returns 422."""
        response = await client.post(
            "/api/v1/public/analyze",
            json={"github_username": "user@invalid!"},
        )
        assert response.status_code == 422

    async def test_analyze_user_not_found(self, client):
        """Non-existent GitHub user returns 404."""
        from app.exceptions import GitHubAPIError

        mock_github = AsyncMock()
        mock_github.fetch_profile.side_effect = GitHubAPIError(
            message="GitHub user not found",
            status_code=404,
        )

        with patch("api.v1.routes.analyze.get_github_service", return_value=mock_github):
            response = await client.post(
                "/api/v1/public/analyze",
                json={"github_username": "nonexistent_user_12345"},
            )

        assert response.status_code == 404

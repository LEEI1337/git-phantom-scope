"""Tests for the GitHub service."""

import pytest
import respx
from httpx import Response

from services.github_service import GitHubService


@pytest.fixture
def github_service(fake_redis):
    """Provide GitHub service with fake Redis."""
    return GitHubService(
        token="ghp_test_token",
        redis=fake_redis,
    )


class TestGitHubService:
    """Test suite for GitHubService."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_profile_success(self, github_service):
        """Successful profile fetch returns user data."""
        respx.get("https://api.github.com/users/testuser").mock(
            return_value=Response(200, json={
                "login": "testuser",
                "public_repos": 42,
                "followers": 100,
                "following": 50,
                "created_at": "2020-01-01T00:00:00Z",
                "bio": "Developer",
            })
        )
        profile = await github_service.fetch_profile("testuser")
        assert profile["login"] == "testuser"
        assert profile["public_repos"] == 42

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_profile_not_found(self, github_service):
        """Non-existent user raises appropriate error."""
        respx.get("https://api.github.com/users/nonexistent").mock(
            return_value=Response(404, json={"message": "Not Found"})
        )
        with pytest.raises(Exception):
            await github_service.fetch_profile("nonexistent")

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_repos(self, github_service):
        """Repository fetch returns list of repos."""
        respx.get("https://api.github.com/users/testuser/repos").mock(
            return_value=Response(200, json=[
                {
                    "name": "repo-1",
                    "language": "Python",
                    "stargazers_count": 10,
                    "forks_count": 3,
                    "topics": ["python"],
                },
                {
                    "name": "repo-2",
                    "language": "TypeScript",
                    "stargazers_count": 5,
                    "forks_count": 1,
                    "topics": ["typescript", "react"],
                },
            ])
        )
        repos = await github_service.fetch_repos("testuser")
        assert len(repos) == 2
        assert repos[0]["name"] == "repo-1"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_events(self, github_service):
        """Event fetch returns list of events."""
        respx.get("https://api.github.com/users/testuser/events/public").mock(
            return_value=Response(200, json=[
                {"type": "PushEvent", "created_at": "2025-08-15T12:00:00Z"},
                {"type": "PullRequestEvent", "created_at": "2025-08-14T12:00:00Z"},
            ])
        )
        events = await github_service.fetch_events("testuser")
        assert len(events) == 2
        assert events[0]["type"] == "PushEvent"

    @respx.mock
    @pytest.mark.asyncio
    async def test_caching_profile(self, github_service):
        """Second fetch should hit cache instead of API."""
        route = respx.get("https://api.github.com/users/cached_user").mock(
            return_value=Response(200, json={
                "login": "cached_user",
                "public_repos": 10,
                "followers": 5,
                "following": 3,
                "created_at": "2023-01-01T00:00:00Z",
            })
        )
        await github_service.fetch_profile("cached_user")
        await github_service.fetch_profile("cached_user")
        assert route.call_count == 1  # Only one actual API call

    @respx.mock
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, github_service):
        """Rate limit response is handled gracefully."""
        respx.get("https://api.github.com/users/limited").mock(
            return_value=Response(
                403,
                json={"message": "API rate limit exceeded"},
                headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "9999999999"},
            )
        )
        with pytest.raises(Exception):
            await github_service.fetch_profile("limited")

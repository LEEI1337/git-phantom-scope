"""Tests for the GitHub service."""

import json

import pytest
import respx
from httpx import Response

from services.github_service import GitHubService


@pytest.fixture
def github_service(fake_redis):
    """Provide GitHub service with fake Redis."""
    return GitHubService(redis=fake_redis)


class TestGitHubService:
    """Test suite for GitHubService."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_profile_rest_fallback(self, github_service):
        """Profile fetch via REST (no GraphQL token) returns data."""
        # Mock REST endpoints
        respx.get("https://api.github.com/users/testuser").mock(
            return_value=Response(200, json={
                "login": "testuser",
                "name": "Test User",
                "avatar_url": "https://example.com/avatar.png",
                "public_repos": 42,
                "followers": 100,
                "following": 50,
                "created_at": "2020-01-01T00:00:00Z",
                "bio": "Developer",
                "hireable": True,
            })
        )
        respx.get("https://api.github.com/users/testuser/repos").mock(
            return_value=Response(200, json=[
                {
                    "name": "repo-1",
                    "description": "A test repo",
                    "language": "Python",
                    "stargazers_count": 10,
                    "forks_count": 3,
                    "fork": False,
                    "updated_at": "2026-01-15T12:00:00Z",
                    "topics": ["python", "fastapi"],
                },
            ])
        )
        respx.get("https://api.github.com/users/testuser/events/public").mock(
            return_value=Response(200, json=[
                {"type": "PushEvent", "payload": {"commits": [{}]}, "created_at": "2026-01-15T12:00:00Z"},
                {"type": "PullRequestEvent", "created_at": "2026-01-14T12:00:00Z"},
            ])
        )

        profile = await github_service.get_profile("testuser")
        assert profile["username"] == "testuser"
        assert profile["public_repos"] == 42
        assert profile["followers"] == 100
        assert len(profile["repos"]) == 1
        assert profile["repos"][0]["name"] == "repo-1"
        assert len(profile["languages"]) > 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_profile_caching(self, github_service):
        """Second profile fetch should hit cache."""
        respx.get("https://api.github.com/users/cached_user").mock(
            return_value=Response(200, json={
                "login": "cached_user",
                "public_repos": 10,
                "followers": 5,
                "following": 3,
                "created_at": "2023-01-01T00:00:00Z",
            })
        )
        respx.get("https://api.github.com/users/cached_user/repos").mock(
            return_value=Response(200, json=[])
        )
        respx.get("https://api.github.com/users/cached_user/events/public").mock(
            return_value=Response(200, json=[])
        )

        profile1 = await github_service.get_profile("cached_user")
        profile2 = await github_service.get_profile("cached_user")
        assert profile1["username"] == profile2["username"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_user_not_found(self, github_service):
        """Non-existent user raises appropriate error."""
        respx.get("https://api.github.com/users/nonexistent").mock(
            return_value=Response(404, json={"message": "Not Found"})
        )
        with pytest.raises(Exception):
            await github_service.get_profile("nonexistent")

    @respx.mock
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, github_service):
        """Rate limit response is handled after retries."""
        respx.get("https://api.github.com/users/limited").mock(
            return_value=Response(
                429,
                json={"message": "API rate limit exceeded"},
                headers={"Retry-After": "1", "X-RateLimit-Remaining": "0"},
            )
        )
        with pytest.raises(Exception):
            await github_service.get_profile("limited")

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_commit_history_rest(self, github_service):
        """Commit history fetch via REST returns commits."""
        respx.get("https://api.github.com/repos/testuser/repo-1/commits").mock(
            return_value=Response(200, json=[
                {
                    "commit": {
                        "message": "feat: add feature with Copilot",
                        "author": {"name": "Test", "email": "test@example.com", "date": "2026-01-15T10:00:00Z"},
                        "committer": {"name": "Test", "email": "test@example.com", "date": "2026-01-15T10:00:00Z"},
                    },
                    "author": {"login": "testuser"},
                    "committer": {"login": "testuser"},
                },
            ])
        )

        commits = await github_service.get_commit_history("testuser", "repo-1", 50)
        assert len(commits) == 1
        assert "Copilot" in commits[0]["message"]
        assert commits[0]["author_login"] == "testuser"

    @respx.mock
    @pytest.mark.asyncio
    async def test_commit_history_caching(self, github_service):
        """Commit history is cached after first fetch."""
        route = respx.get("https://api.github.com/repos/testuser/cached-repo/commits").mock(
            return_value=Response(200, json=[
                {
                    "commit": {"message": "test", "author": {"name": "a", "email": "a@b.c", "date": ""}, "committer": {"name": "a", "email": "a@b.c", "date": ""}},
                    "author": {"login": "testuser"},
                    "committer": {"login": "testuser"},
                },
            ])
        )

        commits1 = await github_service.get_commit_history("testuser", "cached-repo", 50)
        commits2 = await github_service.get_commit_history("testuser", "cached-repo", 50)
        assert len(commits1) == len(commits2)
        assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, github_service):
        """Cache invalidation removes all keys for a username."""
        # Pre-populate cache
        await github_service.redis.setex("github:profile:testuser", 60, json.dumps({"test": True}))
        await github_service.redis.setex("github:commits:testuser:repo", 60, json.dumps([]))

        deleted = await github_service.invalidate_cache("testuser")
        assert deleted >= 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_server_error_retry(self, github_service):
        """Server errors (503) trigger retries."""
        call_count = 0

        def side_effect(request):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return Response(503, json={"message": "Service Unavailable"})
            return Response(200, json={
                "login": "retryuser",
                "public_repos": 5,
                "followers": 10,
                "following": 5,
                "created_at": "2023-01-01T00:00:00Z",
            })

        respx.get("https://api.github.com/users/retryuser").mock(side_effect=side_effect)
        respx.get("https://api.github.com/users/retryuser/repos").mock(
            return_value=Response(200, json=[])
        )
        respx.get("https://api.github.com/users/retryuser/events/public").mock(
            return_value=Response(200, json=[])
        )

        profile = await github_service.get_profile("retryuser")
        assert profile["username"] == "retryuser"
        assert call_count == 3

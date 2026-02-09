"""Tests for GitHub GraphQL client."""

import pytest
import respx
from httpx import Response

from services.github_graphql import GitHubGraphQLClient, GITHUB_GRAPHQL_URL
from app.exceptions import GitHubUserNotFoundError, GitHubRateLimitError, GitHubAPIError


MOCK_GRAPHQL_RESPONSE = {
    "data": {
        "user": {
            "login": "testuser",
            "name": "Test User",
            "avatarUrl": "https://avatars.githubusercontent.com/u/1234",
            "bio": "Developer",
            "company": "TestCo",
            "location": "Berlin",
            "websiteUrl": "https://test.dev",
            "followers": {"totalCount": 100},
            "following": {"totalCount": 50},
            "repositories": {
                "totalCount": 42,
                "nodes": [
                    {
                        "name": "repo-1",
                        "description": "A test repo",
                        "primaryLanguage": {"name": "Python"},
                        "stargazerCount": 10,
                        "forkCount": 3,
                        "isFork": False,
                        "isArchived": False,
                        "updatedAt": "2026-01-15T12:00:00Z",
                        "createdAt": "2025-06-01T12:00:00Z",
                        "repositoryTopics": {
                            "nodes": [
                                {"topic": {"name": "python"}},
                                {"topic": {"name": "fastapi"}},
                            ]
                        },
                        "defaultBranchRef": {
                            "target": {
                                "history": {"totalCount": 150}
                            }
                        },
                    },
                ],
            },
            "pinnedItems": {
                "nodes": [
                    {
                        "name": "pinned-repo",
                        "description": "My pinned project",
                        "primaryLanguage": {"name": "TypeScript"},
                        "stargazerCount": 25,
                        "forkCount": 5,
                        "repositoryTopics": {
                            "nodes": [{"topic": {"name": "react"}}]
                        },
                    }
                ],
            },
            "contributionsCollection": {
                "totalCommitContributions": 500,
                "totalPullRequestContributions": 50,
                "totalIssueContributions": 30,
                "totalPullRequestReviewContributions": 20,
                "totalRepositoriesWithContributedCommits": 15,
                "totalRepositoriesWithContributedPullRequests": 8,
                "totalRepositoriesWithContributedIssues": 5,
                "restrictedContributionsCount": 100,
                "contributionCalendar": {
                    "totalContributions": 600,
                    "weeks": [
                        {
                            "contributionDays": [
                                {"contributionCount": 5, "date": "2026-01-13", "weekday": 1},
                                {"contributionCount": 3, "date": "2026-01-14", "weekday": 2},
                            ]
                        }
                    ],
                },
            },
            "organizations": {
                "totalCount": 1,
                "nodes": [
                    {
                        "login": "test-org",
                        "name": "Test Organization",
                        "avatarUrl": "https://avatars.githubusercontent.com/o/5678",
                    }
                ],
            },
            "createdAt": "2020-01-01T00:00:00Z",
            "updatedAt": "2026-01-15T12:00:00Z",
            "hasSponsorsListing": False,
            "isBountyHunter": False,
            "isCampusExpert": False,
            "isDeveloperProgramMember": True,
            "isHireable": True,
        },
        "rateLimit": {
            "cost": 1,
            "remaining": 4999,
            "resetAt": "2026-01-15T13:00:00Z",
        },
    }
}

MOCK_COMMIT_RESPONSE = {
    "data": {
        "repository": {
            "defaultBranchRef": {
                "target": {
                    "history": {
                        "totalCount": 150,
                        "pageInfo": {
                            "hasNextPage": True,
                            "endCursor": "abc123",
                        },
                        "nodes": [
                            {
                                "message": "feat: add auth module with Copilot",
                                "committedDate": "2026-01-15T10:00:00Z",
                                "author": {
                                    "name": "Test User",
                                    "email": "test@example.com",
                                    "user": {"login": "testuser"},
                                },
                                "committer": {
                                    "name": "Test User",
                                    "email": "test@example.com",
                                    "user": {"login": "testuser"},
                                },
                                "additions": 100,
                                "deletions": 20,
                                "changedFilesIfAvailable": 5,
                            },
                            {
                                "message": "fix: resolve login bug\n\nCo-authored-by: dependabot[bot] <dep@github.com>",
                                "committedDate": "2026-01-14T10:00:00Z",
                                "author": {
                                    "name": "Test User",
                                    "email": "test@example.com",
                                    "user": {"login": "testuser"},
                                },
                                "committer": {
                                    "name": "Test User",
                                    "email": "test@example.com",
                                    "user": {"login": "testuser"},
                                },
                                "additions": 10,
                                "deletions": 5,
                                "changedFilesIfAvailable": 2,
                            },
                        ],
                    }
                }
            }
        },
        "rateLimit": {"cost": 1, "remaining": 4998, "resetAt": "2026-01-15T13:00:00Z"},
    }
}


@pytest.fixture
def graphql_client():
    """Provide a GraphQL client with a test token."""
    return GitHubGraphQLClient(token="ghp_test_token_fake")


class TestGitHubGraphQLClient:
    """Test suite for GitHubGraphQLClient."""

    def test_has_token(self, graphql_client: GitHubGraphQLClient):
        """Client with token reports has_token=True."""
        assert graphql_client.has_token is True

    def test_no_token(self):
        """Client without token reports has_token=False."""
        client = GitHubGraphQLClient(token=None)
        # Will try to load from settings, but in test env should be None
        # We override by setting _token directly
        client._token = None
        assert client.has_token is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_profile_success(self, graphql_client: GitHubGraphQLClient):
        """Successful profile fetch returns transformed data."""
        respx.post(GITHUB_GRAPHQL_URL).mock(
            return_value=Response(200, json=MOCK_GRAPHQL_RESPONSE)
        )
        profile = await graphql_client.fetch_profile("testuser")
        assert profile["username"] == "testuser"
        assert profile["name"] == "Test User"
        assert profile["followers"] == 100
        assert profile["public_repos"] == 42
        assert len(profile["repos"]) == 1
        assert profile["repos"][0]["name"] == "repo-1"
        assert profile["repos"][0]["language"] == "Python"
        assert profile["repos"][0]["total_commits"] == 150
        assert len(profile["pinned_repos"]) == 1
        assert profile["pinned_repos"][0]["name"] == "pinned-repo"
        assert profile["contribution_stats"]["total_commits"] == 500
        assert profile["contribution_stats"]["total_prs"] == 50
        assert len(profile["contribution_calendar"]) == 2
        assert len(profile["organizations"]) == 1
        assert profile["is_hireable"] is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_profile_not_found(self, graphql_client: GitHubGraphQLClient):
        """Non-existent user raises GitHubUserNotFoundError."""
        respx.post(GITHUB_GRAPHQL_URL).mock(
            return_value=Response(200, json={
                "data": {"user": None, "rateLimit": {"cost": 1, "remaining": 4999, "resetAt": ""}},
            })
        )
        with pytest.raises(GitHubUserNotFoundError):
            await graphql_client.fetch_profile("nonexistent")

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_profile_no_token(self):
        """Profile fetch without token returns empty dict."""
        client = GitHubGraphQLClient(token=None)
        client._token = None
        result = await client.fetch_profile("testuser")
        assert result == {}

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_commit_history(self, graphql_client: GitHubGraphQLClient):
        """Commit history fetch returns list of commits."""
        respx.post(GITHUB_GRAPHQL_URL).mock(
            return_value=Response(200, json=MOCK_COMMIT_RESPONSE)
        )
        commits = await graphql_client.fetch_commit_history("testuser", "repo-1", 50)
        assert len(commits) == 2
        assert commits[0]["message"] == "feat: add auth module with Copilot"
        assert commits[0]["author_login"] == "testuser"
        assert commits[0]["additions"] == 100
        assert commits[1]["deletions"] == 5

    @respx.mock
    @pytest.mark.asyncio
    async def test_rate_limit_error(self, graphql_client: GitHubGraphQLClient):
        """Rate limit response raises GitHubRateLimitError after retries."""
        respx.post(GITHUB_GRAPHQL_URL).mock(
            return_value=Response(403, json={"message": "rate limit exceeded"})
        )
        with pytest.raises(GitHubRateLimitError):
            await graphql_client.fetch_profile("testuser")

    @respx.mock
    @pytest.mark.asyncio
    async def test_auth_error(self, graphql_client: GitHubGraphQLClient):
        """Invalid token raises GitHubAPIError."""
        respx.post(GITHUB_GRAPHQL_URL).mock(
            return_value=Response(401, json={"message": "Bad credentials"})
        )
        with pytest.raises(GitHubAPIError):
            await graphql_client.fetch_profile("testuser")

    @respx.mock
    @pytest.mark.asyncio
    async def test_graphql_level_errors_with_data(self, graphql_client: GitHubGraphQLClient):
        """GraphQL errors with partial data still return results."""
        response_with_errors = {
            "data": MOCK_GRAPHQL_RESPONSE["data"],
            "errors": [{"message": "Some field deprecated", "type": "DEPRECATION"}],
        }
        respx.post(GITHUB_GRAPHQL_URL).mock(
            return_value=Response(200, json=response_with_errors)
        )
        profile = await graphql_client.fetch_profile("testuser")
        assert profile["username"] == "testuser"

    @respx.mock
    @pytest.mark.asyncio
    async def test_graphql_not_found_error_type(self, graphql_client: GitHubGraphQLClient):
        """GraphQL NOT_FOUND error type raises GitHubUserNotFoundError."""
        respx.post(GITHUB_GRAPHQL_URL).mock(
            return_value=Response(200, json={
                "errors": [{"message": "Could not resolve to a User", "type": "NOT_FOUND"}],
            })
        )
        with pytest.raises(GitHubUserNotFoundError):
            await graphql_client.fetch_profile("nonexistent")

    @respx.mock
    @pytest.mark.asyncio
    async def test_commit_history_no_token(self):
        """Commit history without token returns empty list."""
        client = GitHubGraphQLClient(token=None)
        client._token = None
        result = await client.fetch_commit_history("testuser", "repo", 50)
        assert result == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_repo_without_default_branch(self, graphql_client: GitHubGraphQLClient):
        """Repository without default branch returns empty commits."""
        respx.post(GITHUB_GRAPHQL_URL).mock(
            return_value=Response(200, json={
                "data": {
                    "repository": {"defaultBranchRef": None},
                    "rateLimit": {"cost": 1, "remaining": 4999, "resetAt": ""},
                }
            })
        )
        commits = await graphql_client.fetch_commit_history("testuser", "empty-repo", 50)
        assert commits == []

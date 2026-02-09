"""GitHub GraphQL API Client.

Provides richer profile data than the REST API:
- Contribution calendar (heatmap)
- Total contribution counts (all time)
- Pinned repositories
- Commit history with messages (for AI detection)
- Organization memberships (public)
- Sponsorship info

Includes exponential backoff retry logic for rate limits.

PRIVACY: All data is temporary (Redis TTL). NO PII persisted.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

from app.config import get_settings
from app.exceptions import GitHubAPIError, GitHubRateLimitError, GitHubUserNotFoundError
from app.logging_config import get_logger
from app.metrics import GITHUB_API_CALLS, GITHUB_API_DURATION

logger = get_logger(__name__)

# GraphQL endpoint
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

# --- GraphQL Queries ---

PROFILE_QUERY = """
query UserProfile($login: String!) {
  user(login: $login) {
    login
    name
    avatarUrl
    bio
    company
    location
    websiteUrl
    followers { totalCount }
    following { totalCount }
    repositories(
      first: 100
      ownerAffiliations: OWNER
      orderBy: { field: UPDATED_AT, direction: DESC }
      privacy: PUBLIC
    ) {
      totalCount
      nodes {
        name
        description
        primaryLanguage { name }
        stargazerCount
        forkCount
        isFork
        isArchived
        updatedAt
        createdAt
        repositoryTopics(first: 10) {
          nodes { topic { name } }
        }
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 0) { totalCount }
            }
          }
        }
      }
    }
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          description
          primaryLanguage { name }
          stargazerCount
          forkCount
          repositoryTopics(first: 10) {
            nodes { topic { name } }
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      totalRepositoriesWithContributedCommits
      totalRepositoriesWithContributedPullRequests
      totalRepositoriesWithContributedIssues
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
            weekday
          }
        }
      }
    }
    organizations(first: 10) {
      totalCount
      nodes {
        login
        name
        avatarUrl
      }
    }
    createdAt
    updatedAt
    hasSponsorsListing
    isBountyHunter
    isCampusExpert
    isDeveloperProgramMember
    isHireable
  }
  rateLimit {
    cost
    remaining
    resetAt
  }
}
"""

COMMIT_HISTORY_QUERY = """
query RepoCommits($owner: String!, $name: String!, $first: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: $first, after: $after) {
            totalCount
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              message
              committedDate
              author {
                name
                email
                user { login }
              }
              committer {
                name
                email
                user { login }
              }
              additions
              deletions
              changedFilesIfAvailable
            }
          }
        }
      }
    }
  }
  rateLimit {
    cost
    remaining
    resetAt
  }
}
"""

CONTRIBUTION_YEARS_QUERY = """
query ContributionYears($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionYears
    }
  }
}
"""

CONTRIBUTION_YEAR_QUERY = """
query ContributionsByYear($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
      }
    }
  }
}
"""


class GitHubGraphQLClient:
    """Client for GitHub GraphQL API (v4).

    Requires a valid GitHub token (PAT or OAuth) for authentication.
    GraphQL API has no unauthenticated access.
    """

    def __init__(self, token: str | None = None) -> None:
        settings = get_settings()
        self._token = token
        if not self._token and settings.github_token:
            self._token = settings.github_token.get_secret_value()

        self._headers = {
            "Accept": "application/json",
        }
        if self._token:
            self._headers["Authorization"] = f"Bearer {self._token}"

    @property
    def has_token(self) -> bool:
        """Check if a valid token is configured."""
        return bool(self._token)

    async def fetch_profile(self, username: str) -> dict[str, Any]:
        """Fetch enriched profile data via GraphQL.

        Returns user data with contributions, pinned repos,
        and contribution calendar. Falls back gracefully if
        GraphQL is unavailable (no token).
        """
        if not self.has_token:
            logger.info("graphql_skipped_no_token")
            return {}

        data = await self._execute(PROFILE_QUERY, {"login": username})

        user = data.get("user")
        if user is None:
            raise GitHubUserNotFoundError()

        return self._transform_profile(user)

    async def fetch_commit_history(
        self,
        owner: str,
        repo_name: str,
        count: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch recent commits for a repository.

        Used for commit message AI detection and co-author parsing.

        Args:
            owner: Repository owner (username)
            repo_name: Repository name
            count: Number of commits to fetch (max 100)

        Returns:
            List of commit dicts with message, author, date info
        """
        if not self.has_token:
            return []

        count = min(count, 100)
        data = await self._execute(
            COMMIT_HISTORY_QUERY,
            {"owner": owner, "name": repo_name, "first": count, "after": None},
        )

        repo = data.get("repository")
        if not repo:
            return []

        branch_ref = repo.get("defaultBranchRef")
        if not branch_ref:
            return []

        target = branch_ref.get("target", {})
        history = target.get("history", {})
        nodes = history.get("nodes", [])

        return [
            {
                "message": c.get("message", ""),
                "committed_date": c.get("committedDate", ""),
                "author_name": c.get("author", {}).get("name", ""),
                "author_login": (c.get("author", {}).get("user") or {}).get("login", ""),
                "committer_name": c.get("committer", {}).get("name", ""),
                "committer_login": (c.get("committer", {}).get("user") or {}).get("login", ""),
                "additions": c.get("additions", 0),
                "deletions": c.get("deletions", 0),
                "changed_files": c.get("changedFilesIfAvailable", 0),
            }
            for c in nodes
        ]

    async def fetch_contribution_years(self, username: str) -> list[int]:
        """Fetch all years a user has contributions."""
        if not self.has_token:
            return []

        data = await self._execute(CONTRIBUTION_YEARS_QUERY, {"login": username})
        user = data.get("user")
        if not user:
            return []

        return user.get("contributionsCollection", {}).get("contributionYears", [])

    async def _execute(
        self,
        query: str,
        variables: dict[str, Any],
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Execute a GraphQL query with retry logic.

        Retries on rate limits (403) and server errors (502/503/504)
        with exponential backoff.
        """
        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            async with httpx.AsyncClient(timeout=30.0) as client:
                with GITHUB_API_DURATION.labels(endpoint="graphql").time():
                    try:
                        response = await client.post(
                            GITHUB_GRAPHQL_URL,
                            headers=self._headers,
                            json={"query": query, "variables": variables},
                        )
                    except httpx.RequestError as exc:
                        GITHUB_API_CALLS.labels(endpoint="graphql", status="error").inc()
                        last_exception = exc
                        if attempt < max_retries:
                            wait = self._backoff_delay(attempt)
                            logger.warning(
                                "graphql_connection_retry",
                                attempt=attempt + 1,
                                wait_seconds=wait,
                            )
                            await asyncio.sleep(wait)
                            continue
                        raise GitHubAPIError(
                            "GitHub GraphQL API connection failed after retries"
                        ) from exc

                status = response.status_code
                GITHUB_API_CALLS.labels(endpoint="graphql", status=str(status)).inc()

                if status == 401:
                    raise GitHubAPIError("GitHub token invalid or expired", status_code=401)

                # Retryable: rate limit or server errors
                if status in (403, 429, 502, 503, 504):
                    if attempt < max_retries:
                        wait = self._backoff_delay(attempt, base=2.0)
                        logger.warning(
                            "graphql_retryable_error",
                            attempt=attempt + 1,
                            wait_seconds=wait,
                            status=status,
                        )
                        await asyncio.sleep(wait)
                        continue

                    if status in (403, 429):
                        raise GitHubRateLimitError()
                    raise GitHubAPIError(
                        f"GitHub GraphQL API returned status {status}",
                        status_code=status,
                    )

                if status >= 400:
                    raise GitHubAPIError(
                        f"GitHub GraphQL API returned status {status}",
                        status_code=status,
                    )

                body = response.json()

                # Check for GraphQL-level errors
                errors = body.get("errors")
                if errors:
                    error_types = [e.get("type", "") for e in errors]
                    if "NOT_FOUND" in error_types:
                        raise GitHubUserNotFoundError()
                    if "RATE_LIMITED" in error_types:
                        if attempt < max_retries:
                            wait = self._backoff_delay(attempt, base=5.0)
                            logger.warning(
                                "graphql_rate_limited_retry",
                                attempt=attempt + 1,
                                wait_seconds=wait,
                            )
                            await asyncio.sleep(wait)
                            continue
                        raise GitHubRateLimitError()

                    error_messages = "; ".join(e.get("message", "") for e in errors)
                    logger.warning("graphql_errors", errors=error_messages)

                    if not body.get("data"):
                        raise GitHubAPIError(f"GraphQL errors: {error_messages}")

                # Log rate limit info
                rate_limit = body.get("data", {}).get("rateLimit")
                if rate_limit:
                    remaining = rate_limit.get("remaining", 0)
                    if remaining < 100:
                        logger.warning(
                            "graphql_rate_limit_low",
                            remaining=remaining,
                            reset_at=rate_limit.get("resetAt"),
                        )

                return body.get("data", {})

        raise GitHubAPIError("GitHub GraphQL request failed") from last_exception

    @staticmethod
    def _backoff_delay(attempt: int, base: float = 1.0, max_delay: float = 30.0) -> float:
        """Calculate exponential backoff delay with jitter."""
        delay = base * (2**attempt)
        jitter = random.uniform(0, delay * 0.1)
        return min(delay + jitter, max_delay)

    def _transform_profile(self, user: dict[str, Any]) -> dict[str, Any]:
        """Transform raw GraphQL user data into our profile format."""
        contributions = user.get("contributionsCollection", {})
        calendar = contributions.get("contributionCalendar", {})

        # Transform repos
        repos_data = user.get("repositories", {})
        repos = []
        for node in repos_data.get("nodes", []):
            topics = [t["topic"]["name"] for t in node.get("repositoryTopics", {}).get("nodes", [])]
            primary_lang = node.get("primaryLanguage")
            lang_name = primary_lang["name"] if primary_lang else None

            # Get total commit count for repo
            branch_ref = node.get("defaultBranchRef")
            total_commits = 0
            if branch_ref:
                target = branch_ref.get("target", {})
                total_commits = target.get("history", {}).get("totalCount", 0)

            repos.append(
                {
                    "name": node.get("name", ""),
                    "description": node.get("description"),
                    "language": lang_name,
                    "stars": node.get("stargazerCount", 0),
                    "forks": node.get("forkCount", 0),
                    "is_fork": node.get("isFork", False),
                    "is_archived": node.get("isArchived", False),
                    "updated_at": node.get("updatedAt"),
                    "created_at": node.get("createdAt"),
                    "topics": topics,
                    "total_commits": total_commits,
                }
            )

        # Transform pinned repos
        pinned = []
        for node in user.get("pinnedItems", {}).get("nodes", []):
            primary_lang = node.get("primaryLanguage")
            lang_name = primary_lang["name"] if primary_lang else None
            topics = [t["topic"]["name"] for t in node.get("repositoryTopics", {}).get("nodes", [])]
            pinned.append(
                {
                    "name": node.get("name", ""),
                    "description": node.get("description"),
                    "language": lang_name,
                    "stars": node.get("stargazerCount", 0),
                    "forks": node.get("forkCount", 0),
                    "topics": topics,
                }
            )

        # Transform contribution calendar to heatmap
        contribution_days = []
        for week in calendar.get("weeks", []):
            for day in week.get("contributionDays", []):
                contribution_days.append(
                    {
                        "date": day.get("date"),
                        "count": day.get("contributionCount", 0),
                        "weekday": day.get("weekday", 0),
                    }
                )

        # Transform organizations
        orgs = [
            {
                "login": o.get("login", ""),
                "name": o.get("name"),
                "avatar_url": o.get("avatarUrl", ""),
            }
            for o in user.get("organizations", {}).get("nodes", [])
        ]

        return {
            "username": user.get("login", ""),
            "name": user.get("name"),
            "avatar_url": user.get("avatarUrl", ""),
            "bio": user.get("bio"),
            "company": user.get("company"),
            "location": user.get("location"),
            "blog": user.get("websiteUrl"),
            "created_at": user.get("createdAt"),
            "is_hireable": user.get("isHireable", False),
            "is_developer_program_member": user.get("isDeveloperProgramMember", False),
            "has_sponsors_listing": user.get("hasSponsorsListing", False),
            "followers": user.get("followers", {}).get("totalCount", 0),
            "following": user.get("following", {}).get("totalCount", 0),
            "public_repos": repos_data.get("totalCount", 0),
            "repos": repos,
            "pinned_repos": pinned,
            "organizations": orgs,
            "contribution_stats": {
                "total_commits": contributions.get("totalCommitContributions", 0),
                "total_prs": contributions.get("totalPullRequestContributions", 0),
                "total_issues": contributions.get("totalIssueContributions", 0),
                "total_reviews": contributions.get("totalPullRequestReviewContributions", 0),
                "repos_contributed_to": contributions.get(
                    "totalRepositoriesWithContributedCommits", 0
                ),
                "private_contributions": contributions.get("restrictedContributionsCount", 0),
                "total_contributions_last_year": calendar.get("totalContributions", 0),
                "period": "last_year",
            },
            "contribution_calendar": contribution_days,
        }

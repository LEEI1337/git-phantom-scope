"""GitHub Data Service.

Fetches public profile data from GitHub REST and GraphQL APIs.
Implements multi-tier caching via Redis with configurable TTLs.
Prefers GraphQL for richer data when a token is available,
falls back to REST API for unauthenticated requests.

PRIVACY: All fetched data is temporary (Redis TTL).
NO GitHub data is persisted to PostgreSQL.
"""

from __future__ import annotations

import asyncio
import json
import zlib
from datetime import datetime
from typing import Any, Optional

import httpx
import redis.asyncio as aioredis

from app.config import get_settings
from app.exceptions import (
    GitHubAPIError,
    GitHubRateLimitError,
    GitHubUserNotFoundError,
)
from app.logging_config import get_logger
from app.metrics import (
    GITHUB_API_CALLS,
    GITHUB_API_DURATION,
    GITHUB_CACHE_HITS,
    GITHUB_CACHE_MISSES,
)
from services.github_graphql import GitHubGraphQLClient

logger = get_logger(__name__)

# Cache TTL tiers (seconds)
CACHE_TTL_PROFILE = 900       # 15 min - full profile
CACHE_TTL_COMMITS = 600       # 10 min - commit history
CACHE_TTL_CALENDAR = 1800     # 30 min - contribution calendar (changes slowly)
CACHE_COMPRESS_THRESHOLD = 4096  # Compress payloads > 4KB


class GitHubService:
    """Service for fetching and caching GitHub profile data.

    Uses GraphQL API (v4) when a token is available for richer data.
    Falls back to REST API (v3) for unauthenticated requests.

    Cache strategy:
    - Profile: 15 min TTL (github:profile:{username})
    - Commits: 10 min TTL (github:commits:{username}:{repo})
    - Calendar: 30 min TTL (github:calendar:{username})
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis
        self.settings = get_settings()
        self._graphql = GitHubGraphQLClient()
        self._headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.settings.github_token:
            self._headers["Authorization"] = (
                f"Bearer {self.settings.github_token.get_secret_value()}"
            )

    # --- Cache Helpers ---

    async def _cache_get(self, key: str) -> Any | None:
        """Get value from Redis cache with optional decompression."""
        raw = await self.redis.get(key)
        if raw is None:
            GITHUB_CACHE_MISSES.inc()
            return None

        GITHUB_CACHE_HITS.inc()

        # Check for compression marker
        if isinstance(raw, bytes) and raw[:2] == b"\x78\x9c":
            try:
                raw = zlib.decompress(raw)
            except zlib.error:
                pass

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        return json.loads(raw)

    async def _cache_set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in Redis cache with optional compression."""
        serialized = json.dumps(value, separators=(",", ":"))

        # Compress large payloads
        if len(serialized) > CACHE_COMPRESS_THRESHOLD:
            data: bytes | str = zlib.compress(serialized.encode("utf-8"), level=6)
        else:
            data = serialized

        await self.redis.setex(key, ttl, data)

    async def invalidate_cache(self, username: str) -> int:
        """Invalidate all cached data for a username.

        Returns number of keys deleted.
        """
        pattern = f"github:*:{username}*"
        keys = []
        async for key in self.redis.scan_iter(match=pattern, count=100):
            keys.append(key)
        if keys:
            return await self.redis.delete(*keys)
        return 0

    async def get_profile(self, username: str) -> dict[str, Any]:
        """Fetch complete GitHub profile data.

        Strategy:
        1. Check Redis cache first
        2. Try GraphQL API (richer data, requires token)
        3. Fall back to REST API if GraphQL unavailable
        """
        cache_key = f"github:profile:{username}"
        cached = await self._cache_get(cache_key)

        if cached:
            logger.debug("github_cache_hit", cache_key=cache_key)
            return cached

        # Try GraphQL first (richer data)
        profile: dict[str, Any] = {}
        if self._graphql.has_token:
            try:
                profile = await self._graphql.fetch_profile(username)
                # GraphQL doesn't return aggregated languages, compute from repos
                if profile and "languages" not in profile:
                    profile["languages"] = self._aggregate_languages(
                        profile.get("repos", [])
                    )
                logger.info("github_graphql_profile_fetched", username_len=len(username))
            except (GitHubAPIError, GitHubRateLimitError) as exc:
                logger.warning(
                    "github_graphql_fallback_to_rest",
                    error=str(exc),
                )
                profile = {}
            except GitHubUserNotFoundError:
                raise

        # Fall back to REST if GraphQL didn't return data
        if not profile:
            profile = await self._build_rest_profile(username)

        profile["fetched_at"] = datetime.utcnow().isoformat()

        # Cache with tiered TTL
        await self._cache_set(cache_key, profile, CACHE_TTL_PROFILE)

        return profile

    async def get_commit_history(
        self,
        username: str,
        repo_name: str,
        count: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch commit history for AI detection and co-author parsing.

        Uses GraphQL for detailed commit data including messages.
        Falls back to REST Events API if GraphQL unavailable.
        """
        cache_key = f"github:commits:{username}:{repo_name}"
        cached = await self._cache_get(cache_key)
        if cached:
            return cached

        commits: list[dict[str, Any]] = []

        if self._graphql.has_token:
            try:
                commits = await self._graphql.fetch_commit_history(
                    username, repo_name, count
                )
            except (GitHubAPIError, GitHubRateLimitError):
                logger.warning("commit_history_graphql_failed", repo=repo_name)

        if not commits:
            commits = await self._fetch_commits_rest(username, repo_name, count)

        # Cache commits (shorter TTL)
        if commits:
            await self._cache_set(cache_key, commits, CACHE_TTL_COMMITS)

        return commits

    async def _build_rest_profile(self, username: str) -> dict[str, Any]:
        """Build profile from REST API (fallback when GraphQL unavailable)."""
        user_data = await self._fetch_user(username)
        repos_data = await self._fetch_repos(username)
        languages = self._aggregate_languages(repos_data)
        contribution_stats = await self._fetch_contribution_stats(username)

        profile = {
            "username": user_data.get("login", ""),
            "name": user_data.get("name"),
            "avatar_url": user_data.get("avatar_url", ""),
            "bio": user_data.get("bio"),
            "company": user_data.get("company"),
            "location": user_data.get("location"),
            "blog": user_data.get("blog"),
            "public_repos": user_data.get("public_repos", 0),
            "followers": user_data.get("followers", 0),
            "following": user_data.get("following", 0),
            "created_at": user_data.get("created_at"),
            "is_hireable": user_data.get("hireable", False),
            "repos": [
                {
                    "name": r.get("name", ""),
                    "description": r.get("description"),
                    "language": r.get("language"),
                    "stars": r.get("stargazers_count", 0),
                    "forks": r.get("forks_count", 0),
                    "is_fork": r.get("fork", False),
                    "updated_at": r.get("updated_at"),
                    "topics": r.get("topics", []),
                }
                for r in repos_data
                if not r.get("fork", False)
            ],
            "languages": languages,
            "contribution_stats": contribution_stats,
            "pinned_repos": [],
            "organizations": [],
            "contribution_calendar": [],
        }

        return profile

    async def _fetch_user(self, username: str) -> dict[str, Any]:
        """Fetch user profile from GitHub REST API."""
        url = f"{self.settings.github_api_base}/users/{username}"
        return await self._api_request(url)

    async def _fetch_repos(
        self, username: str, per_page: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch public repositories, sorted by most recently updated."""
        url = f"{self.settings.github_api_base}/users/{username}/repos"
        params = {
            "sort": "updated",
            "direction": "desc",
            "per_page": per_page,
            "type": "owner",
        }
        return await self._api_request(url, params=params)

    async def _fetch_contribution_stats(self, username: str) -> dict[str, Any]:
        """Fetch contribution statistics via GitHub Events API.

        Note: Events API only returns last 90 days, max 300 events.
        For more detailed stats, GraphQL with auth token is needed.
        """
        url = f"{self.settings.github_api_base}/users/{username}/events/public"
        try:
            events = await self._api_request(url, params={"per_page": 100})
            if not isinstance(events, list):
                events = []

            push_events = [e for e in events if e.get("type") == "PushEvent"]
            pr_events = [e for e in events if e.get("type") == "PullRequestEvent"]
            issue_events = [e for e in events if e.get("type") == "IssuesEvent"]
            review_events = [
                e for e in events if e.get("type") == "PullRequestReviewEvent"
            ]

            total_commits = sum(
                len(e.get("payload", {}).get("commits", []))
                for e in push_events
            )

            return {
                "recent_commits": total_commits,
                "recent_prs": len(pr_events),
                "recent_issues": len(issue_events),
                "recent_reviews": len(review_events),
                "total_events": len(events),
                "period": "last_90_days",
            }
        except Exception:
            logger.warning("contribution_stats_fetch_failed")
            return {
                "recent_commits": 0,
                "recent_prs": 0,
                "recent_issues": 0,
                "recent_reviews": 0,
                "total_events": 0,
                "period": "unavailable",
            }

    async def _fetch_commits_rest(
        self,
        owner: str,
        repo_name: str,
        count: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch commits via REST API (fallback for GraphQL).

        REST commits endpoint provides less detail than GraphQL
        but works without authentication for public repos.
        """
        url = f"{self.settings.github_api_base}/repos/{owner}/{repo_name}/commits"
        try:
            commits_raw = await self._api_request(
                url, params={"per_page": min(count, 100)}
            )
            if not isinstance(commits_raw, list):
                return []

            return [
                {
                    "message": c.get("commit", {}).get("message", ""),
                    "committed_date": c.get("commit", {}).get("committer", {}).get("date", ""),
                    "author_name": c.get("commit", {}).get("author", {}).get("name", ""),
                    "author_login": (c.get("author") or {}).get("login", ""),
                    "committer_name": c.get("commit", {}).get("committer", {}).get("name", ""),
                    "committer_login": (c.get("committer") or {}).get("login", ""),
                    "additions": 0,  # Not available in list endpoint
                    "deletions": 0,
                    "changed_files": 0,
                }
                for c in commits_raw
            ]
        except (GitHubAPIError, GitHubUserNotFoundError):
            logger.warning("commits_rest_fetch_failed", repo=repo_name)
            return []

    def _aggregate_languages(self, repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Aggregate language usage across repositories.

        Also used by GraphQL path to enrich profile if languages
        are not already present from the GraphQL response.
        """
        lang_counts: dict[str, int] = {}
        for repo in repos:
            lang = repo.get("language")
            is_fork = repo.get("fork", False) or repo.get("is_fork", False)
            if lang and not is_fork:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

        total = sum(lang_counts.values()) or 1
        languages = [
            {
                "name": lang,
                "count": count,
                "percentage": round(count / total * 100, 1),
            }
            for lang, count in sorted(
                lang_counts.items(), key=lambda x: x[1], reverse=True
            )
        ]
        return languages

    async def _api_request(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> Any:
        """Make an authenticated request to GitHub API with retry logic.

        Implements exponential backoff for:
        - 429 Too Many Requests
        - 403 Forbidden (rate limit)
        - 502/503/504 Server errors

        Non-retryable errors (404, 401) are raised immediately.
        """
        endpoint = url.split("/")[-1]
        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            async with httpx.AsyncClient(timeout=30.0) as client:
                with GITHUB_API_DURATION.labels(endpoint=endpoint).time():
                    try:
                        response = await client.get(
                            url, headers=self._headers, params=params
                        )
                    except httpx.RequestError as exc:
                        GITHUB_API_CALLS.labels(endpoint=endpoint, status="error").inc()
                        last_exception = exc
                        if attempt < max_retries:
                            wait = self._backoff_delay(attempt)
                            logger.warning(
                                "github_api_connection_retry",
                                attempt=attempt + 1,
                                wait_seconds=wait,
                                endpoint=endpoint,
                            )
                            await asyncio.sleep(wait)
                            continue
                        raise GitHubAPIError(
                            "GitHub API connection failed after retries"
                        ) from exc

                status = response.status_code
                GITHUB_API_CALLS.labels(endpoint=endpoint, status=str(status)).inc()

                # Non-retryable errors
                if status == 404:
                    raise GitHubUserNotFoundError()
                if status == 401:
                    raise GitHubAPIError(
                        "GitHub token invalid or expired", status_code=401
                    )

                # Retryable: rate limit
                if status in (403, 429):
                    retry_after = response.headers.get("Retry-After")
                    rate_remaining = response.headers.get("X-RateLimit-Remaining")

                    if attempt < max_retries:
                        if retry_after:
                            wait = min(int(retry_after), 60)
                        elif rate_remaining == "0":
                            wait = self._backoff_delay(attempt, base=5.0)
                        else:
                            wait = self._backoff_delay(attempt)

                        logger.warning(
                            "github_rate_limit_retry",
                            attempt=attempt + 1,
                            wait_seconds=wait,
                            status=status,
                            endpoint=endpoint,
                        )
                        await asyncio.sleep(wait)
                        continue

                    raise GitHubRateLimitError(
                        retry_after=int(retry_after) if retry_after else None
                    )

                # Retryable: server errors
                if status in (502, 503, 504):
                    if attempt < max_retries:
                        wait = self._backoff_delay(attempt)
                        logger.warning(
                            "github_server_error_retry",
                            attempt=attempt + 1,
                            wait_seconds=wait,
                            status=status,
                            endpoint=endpoint,
                        )
                        await asyncio.sleep(wait)
                        continue

                    raise GitHubAPIError(
                        f"GitHub API server error {status} after retries",
                        status_code=status,
                    )

                # Other client errors
                if status >= 400:
                    raise GitHubAPIError(
                        f"GitHub API returned status {status}",
                        status_code=status,
                    )

                return response.json()

        # Should not reach here, but safety net
        raise GitHubAPIError("GitHub API request failed") from last_exception

    @staticmethod
    def _backoff_delay(attempt: int, base: float = 1.0, max_delay: float = 30.0) -> float:
        """Calculate exponential backoff delay with jitter.

        Formula: min(base * 2^attempt + jitter, max_delay)
        """
        import random

        delay = base * (2 ** attempt)
        jitter = random.uniform(0, delay * 0.1)
        return min(delay + jitter, max_delay)

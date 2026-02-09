"""GitHub Data Service.

Fetches public profile data from GitHub REST and GraphQL APIs.
Implements caching via Redis with configurable TTL.

PRIVACY: All fetched data is temporary (Redis TTL).
NO GitHub data is persisted to PostgreSQL.
"""

from __future__ import annotations

import json
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

logger = get_logger(__name__)


class GitHubService:
    """Service for fetching and caching GitHub profile data."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis
        self.settings = get_settings()
        self._headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.settings.github_token:
            self._headers["Authorization"] = (
                f"Bearer {self.settings.github_token.get_secret_value()}"
            )

    async def get_profile(self, username: str) -> dict[str, Any]:
        """Fetch complete GitHub profile data.

        Returns cached data if available, otherwise fetches from GitHub API.
        """
        cache_key = f"github:profile:{username}"
        cached = await self.redis.get(cache_key)

        if cached:
            GITHUB_CACHE_HITS.inc()
            logger.debug("github_cache_hit", cache_key=cache_key)
            return json.loads(cached)

        GITHUB_CACHE_MISSES.inc()

        # Fetch all profile components
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
            "fetched_at": datetime.utcnow().isoformat(),
        }

        # Cache with TTL
        await self.redis.setex(
            cache_key,
            self.settings.github_cache_ttl,
            json.dumps(profile),
        )

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

    def _aggregate_languages(self, repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Aggregate language usage across repositories."""
        lang_counts: dict[str, int] = {}
        for repo in repos:
            lang = repo.get("language")
            if lang and not repo.get("fork", False):
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
    ) -> Any:
        """Make an authenticated request to GitHub API."""
        endpoint = url.split("/")[-1]

        async with httpx.AsyncClient(timeout=30.0) as client:
            with GITHUB_API_DURATION.labels(endpoint=endpoint).time():
                try:
                    response = await client.get(
                        url, headers=self._headers, params=params
                    )
                except httpx.RequestError as exc:
                    GITHUB_API_CALLS.labels(endpoint=endpoint, status="error").inc()
                    raise GitHubAPIError(
                        "GitHub API connection failed"
                    ) from exc

            status = response.status_code
            GITHUB_API_CALLS.labels(endpoint=endpoint, status=str(status)).inc()

            if status == 404:
                raise GitHubUserNotFoundError()
            if status == 403:
                retry_after = response.headers.get("Retry-After")
                raise GitHubRateLimitError(
                    retry_after=int(retry_after) if retry_after else None
                )
            if status >= 400:
                raise GitHubAPIError(
                    f"GitHub API returned status {status}",
                    status_code=status,
                )

            return response.json()

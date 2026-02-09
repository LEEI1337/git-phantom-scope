"""Profile analysis endpoint.

POST /api/v1/public/analyze - Analyze a GitHub profile
"""

from __future__ import annotations

import json
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.deps import rate_limit_analyze
from app.config import get_settings
from app.dependencies import get_redis
from app.logging_config import get_logger
from services.github_service import GitHubService
from services.scoring_engine import ScoringEngine

logger = get_logger(__name__)
router = APIRouter()


class AnalyzePreferences(BaseModel):
    """User preferences for analysis."""

    career_goal: str | None = Field(None, max_length=200)
    style: str = Field("professional", pattern=r"^(minimal|colorful|professional|creative)$")
    colors: list[str] | None = Field(None, max_items=5)


class BYOKConfig(BaseModel):
    """BYOK key configuration (encrypted)."""

    gemini_key: str | None = None
    openai_key: str | None = None


class AnalyzeRequest(BaseModel):
    """Profile analysis request."""

    github_username: str = Field(
        ..., min_length=1, max_length=39, pattern=r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$"
    )
    preferences: AnalyzePreferences | None = None
    byok: BYOKConfig | None = None


class AnalyzeResponse(BaseModel):
    """Profile analysis response."""

    session_id: str
    profile: dict
    scores: dict
    archetype: dict
    ai_analysis: dict
    tech_profile: dict
    contribution_calendar: list[dict] = []
    pinned_repos: list[dict] = []
    organizations: list[dict] = []
    meta: dict


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_profile(
    request: AnalyzeRequest,
    redis: aioredis.Redis = Depends(get_redis),
    _rate_limit: None = Depends(rate_limit_analyze),
) -> AnalyzeResponse:
    """Analyze a GitHub profile and return scoring data.

    Fetches the public GitHub profile, scores it across 4 dimensions,
    classifies the developer archetype, and detects AI tool usage.

    All data is cached in Redis (TTL: 30 min) and auto-deleted.
    NO data is persisted to PostgreSQL.
    """
    settings = get_settings()

    # Check for cached analysis
    cache_key = f"analysis:{request.github_username}"
    cached = await redis.get(cache_key)
    if cached:
        logger.info("analysis_cache_hit")
        data = json.loads(cached)
        return AnalyzeResponse(**data)

    # Fetch GitHub profile
    github_service = GitHubService(redis)
    profile = await github_service.get_profile(request.github_username)

    # Fetch commit history from top repos for AI detection
    commit_data: list[dict] = []
    top_repos = sorted(
        profile.get("repos", []),
        key=lambda r: r.get("stars", 0),
        reverse=True,
    )[:5]
    for repo in top_repos:
        repo_name = repo.get("name", "")
        if repo_name and not repo.get("is_fork", False):
            commits = await github_service.get_commit_history(
                request.github_username, repo_name, count=30
            )
            commit_data.extend(commits)

    # Score profile with commit analysis
    scoring_engine = ScoringEngine()
    scoring_result = scoring_engine.score_profile(profile, commit_data or None)

    # Create session
    session_id = str(uuid.uuid4())
    session_data = {
        "profile": profile,
        "scoring": scoring_result,
        "preferences": request.preferences.model_dump() if request.preferences else {},
        "byok": request.byok.model_dump() if request.byok else {},
    }

    # Store session in Redis (TTL: 30 min)
    await redis.setex(
        f"session:{session_id}",
        settings.redis_session_ttl,
        json.dumps(session_data),
    )

    # Determine total contributions (prefer GraphQL data)
    contrib_stats = profile.get("contribution_stats", {})
    total_contributions = (
        contrib_stats.get("total_contributions_last_year")
        or contrib_stats.get("total_commits", 0)
        or contrib_stats.get("recent_commits", 0)
    )

    # Build response
    response_data = {
        "session_id": session_id,
        "profile": {
            "username": profile.get("username", ""),
            "avatar_url": profile.get("avatar_url", ""),
            "bio": profile.get("bio"),
            "name": profile.get("name"),
            "company": profile.get("company"),
            "location": profile.get("location"),
            "blog": profile.get("blog"),
            "is_hireable": profile.get("is_hireable", False),
            "created_at": profile.get("created_at"),
            "stats": {
                "repos": profile.get("public_repos", 0),
                "followers": profile.get("followers", 0),
                "following": profile.get("following", 0),
                "contributions_last_year": total_contributions,
                "total_commits": contrib_stats.get("total_commits", 0),
                "total_prs": contrib_stats.get("total_prs", 0),
                "total_issues": contrib_stats.get("total_issues", 0),
                "total_reviews": contrib_stats.get("total_reviews", 0),
            },
        },
        "scores": scoring_result["scores"],
        "archetype": scoring_result["archetype"],
        "ai_analysis": scoring_result.get("ai_analysis", {}),
        "tech_profile": scoring_result.get("tech_profile", {}),
        "contribution_calendar": profile.get("contribution_calendar", []),
        "pinned_repos": profile.get("pinned_repos", []),
        "organizations": profile.get("organizations", []),
        "meta": {
            "request_id": session_id,
            "cache_hit": False,
            "data_source": "graphql" if profile.get("contribution_calendar") else "rest",
        },
    }

    # Cache analysis result (TTL: 30 min)
    await redis.setex(
        cache_key,
        settings.redis_session_ttl,
        json.dumps(response_data),
    )

    logger.info("profile_analyzed", session_id=session_id)
    return AnalyzeResponse(**response_data)

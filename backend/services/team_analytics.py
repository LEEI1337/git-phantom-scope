"""
Git Phantom Scope — Team/Org Analytics Dashboard Service.

Enterprise feature: aggregated team-level analytics and insights
across multiple GitHub profiles within an organization.

Privacy: all data is anonymous and aggregated. No PII stored.
Team membership is tracked via hashed org_id in Redis (session-scoped).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.config import get_settings
from app.exceptions import GPSBaseError


class TeamError(GPSBaseError):
    """Team analytics error."""

    def __init__(self, message: str = "Team analytics error") -> None:
        super().__init__(
            code="TEAM_ERROR",
            message=message,
            status_code=400,
        )


class AggregationPeriod(str, Enum):
    """Time periods for dashboard aggregation."""

    WEEK = "7d"
    MONTH = "30d"
    QUARTER = "90d"
    YEAR = "1y"


class TeamMemberSummary(BaseModel):
    """Anonymous summary of a team member's scores."""

    member_hash: str = Field(..., description="SHA-256 hash of username for privacy")
    scores: dict[str, float] = Field(
        default_factory=dict,
        description="Dimension scores (activity, collaboration, etc.)",
    )
    archetype: str = Field(default="code_explorer")
    ai_tools_detected: list[str] = Field(default_factory=list)
    top_languages: list[str] = Field(default_factory=list)
    analyzed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class TeamDashboard(BaseModel):
    """Aggregated team dashboard data."""

    org_id: str
    team_size: int = 0
    period: str = "30d"
    aggregate_scores: dict[str, float] = Field(default_factory=dict)
    archetype_distribution: dict[str, int] = Field(default_factory=dict)
    ai_adoption_rate: float = 0.0
    top_languages: list[dict[str, Any]] = Field(default_factory=list)
    ai_tools_usage: dict[str, int] = Field(default_factory=dict)
    score_trends: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


_REDIS_PREFIX = "team:"
_MEMBER_PREFIX = "team_member:"
_DASHBOARD_TTL = 1800  # 30 minutes


class TeamAnalyticsService:
    """Manages team-level analytics dashboards for enterprise customers."""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client
        self._settings = get_settings()

    async def add_member_analysis(self, org_id: str, member_summary: TeamMemberSummary) -> str:
        """Add a team member's anonymous analysis to the org dashboard."""
        member_key = f"{_MEMBER_PREFIX}{org_id}:{member_summary.member_hash}"
        data = member_summary.model_dump(mode="json")
        await self._redis.setex(member_key, _DASHBOARD_TTL, json.dumps(data))

        # Track member in org set
        org_set_key = f"{_REDIS_PREFIX}{org_id}:members"
        await self._redis.sadd(org_set_key, member_summary.member_hash)
        await self._redis.expire(org_set_key, _DASHBOARD_TTL)

        return member_summary.member_hash

    async def get_dashboard(
        self, org_id: str, period: AggregationPeriod = AggregationPeriod.MONTH
    ) -> TeamDashboard:
        """Generate aggregated team dashboard from member analyses."""
        members = await self._get_members(org_id)

        if not members:
            return TeamDashboard(org_id=org_id, period=period.value)

        # Aggregate scores
        all_scores: dict[str, list[float]] = {}
        archetypes: dict[str, int] = {}
        all_languages: dict[str, int] = {}
        all_ai_tools: dict[str, int] = {}
        ai_users = 0

        for member in members:
            for dim, score in member.scores.items():
                all_scores.setdefault(dim, []).append(score)

            archetypes[member.archetype] = archetypes.get(member.archetype, 0) + 1

            for lang in member.top_languages:
                all_languages[lang] = all_languages.get(lang, 0) + 1

            for tool in member.ai_tools_detected:
                all_ai_tools[tool] = all_ai_tools.get(tool, 0) + 1

            if member.ai_tools_detected:
                ai_users += 1

        # Calculate averages
        avg_scores = {dim: round(sum(vals) / len(vals), 1) for dim, vals in all_scores.items()}

        # Sort languages by frequency
        sorted_langs = sorted(all_languages.items(), key=lambda x: x[1], reverse=True)
        top_languages = [{"language": lang, "count": count} for lang, count in sorted_langs[:10]]

        team_size = len(members)
        ai_rate = round(ai_users / team_size * 100, 1) if team_size > 0 else 0

        return TeamDashboard(
            org_id=org_id,
            team_size=team_size,
            period=period.value,
            aggregate_scores=avg_scores,
            archetype_distribution=archetypes,
            ai_adoption_rate=ai_rate,
            top_languages=top_languages,
            ai_tools_usage=all_ai_tools,
        )

    async def get_team_comparison(self, org_id: str) -> list[dict[str, Any]]:
        """Get individual (anonymized) member scores for comparison charts."""
        members = await self._get_members(org_id)
        return [
            {
                "id": m.member_hash[:8],
                "scores": m.scores,
                "archetype": m.archetype,
            }
            for m in members
        ]

    async def remove_member(self, org_id: str, member_hash: str) -> bool:
        """Remove a team member's analysis."""
        member_key = f"{_MEMBER_PREFIX}{org_id}:{member_hash}"
        org_set_key = f"{_REDIS_PREFIX}{org_id}:members"
        await self._redis.srem(org_set_key, member_hash)
        result = await self._redis.delete(member_key)
        return result > 0

    async def clear_team(self, org_id: str) -> int:
        """Clear all team analytics data."""
        members = await self._get_member_hashes(org_id)
        deleted = 0
        for member_hash in members:
            key = f"{_MEMBER_PREFIX}{org_id}:{member_hash}"
            deleted += await self._redis.delete(key)
        org_set_key = f"{_REDIS_PREFIX}{org_id}:members"
        await self._redis.delete(org_set_key)
        return deleted

    async def _get_member_hashes(self, org_id: str) -> list[str]:
        """Get all member hashes for an org."""
        org_set_key = f"{_REDIS_PREFIX}{org_id}:members"
        raw_members = await self._redis.smembers(org_set_key)
        return [m.decode() if isinstance(m, bytes) else m for m in raw_members]

    async def _get_members(self, org_id: str) -> list[TeamMemberSummary]:
        """Load all member summaries for an org."""
        hashes = await self._get_member_hashes(org_id)
        members: list[TeamMemberSummary] = []
        for member_hash in hashes:
            key = f"{_MEMBER_PREFIX}{org_id}:{member_hash}"
            raw = await self._redis.get(key)
            if raw:
                data = json.loads(raw)
                members.append(TeamMemberSummary.model_validate(data))
        return members

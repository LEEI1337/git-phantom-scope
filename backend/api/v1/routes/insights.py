"""Public insights endpoint.

GET /api/v1/public/insights - Get aggregated, anonymous AI trend data
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from db.models import AIUsageBucket, TrendSnapshot
from db.session import get_db_session

logger = get_logger(__name__)
router = APIRouter()


class InsightData(BaseModel):
    """Single insight data point."""

    language: str | None = None
    buckets: dict | None = None
    sample_size: int = 0


class InsightsResponse(BaseModel):
    """Aggregated insights response."""

    metric: str
    period: str
    data: list[dict]
    updated_at: str
    meta: dict


@router.get("/insights", response_model=InsightsResponse)
async def get_public_insights(
    metric: str = Query(
        "ai_usage_by_language",
        description="Metric to query",
        pattern=r"^(ai_usage_by_language|archetype_distribution|model_popularity|generation_trends)$",
    ),
    period: str = Query(
        "30d",
        description="Time period",
        pattern=r"^(7d|30d|90d|1y)$",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> InsightsResponse:
    """Get aggregated, anonymous insights about AI usage trends.

    All data is pre-aggregated and contains NO personally
    identifiable information. This endpoint is public.
    """
    period_days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    days = period_days.get(period, 30)
    start_date = date.today() - timedelta(days=days)

    if metric == "ai_usage_by_language":
        data = await _get_ai_usage_by_language(db, start_date)
    elif metric == "archetype_distribution":
        data = await _get_archetype_distribution(db, start_date)
    elif metric == "model_popularity":
        data = await _get_model_popularity(db, start_date)
    elif metric == "generation_trends":
        data = await _get_generation_trends(db, start_date)
    else:
        data = []

    return InsightsResponse(
        metric=metric,
        period=period,
        data=data,
        updated_at=date.today().isoformat(),
        meta={"cache_hit": False},
    )


async def _get_ai_usage_by_language(
    db: AsyncSession, start_date: date
) -> list[dict]:
    """Get AI usage distribution by programming language."""
    stmt = (
        select(
            AIUsageBucket.language,
            AIUsageBucket.ai_bucket,
            func.sum(AIUsageBucket.sample_size).label("total_samples"),
        )
        .where(AIUsageBucket.date >= start_date)
        .group_by(AIUsageBucket.language, AIUsageBucket.ai_bucket)
        .order_by(func.sum(AIUsageBucket.sample_size).desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Group by language
    by_language: dict[str, dict] = {}
    for row in rows:
        lang = row.language
        if lang not in by_language:
            by_language[lang] = {"language": lang, "buckets": {}, "sample_size": 0}
        by_language[lang]["buckets"][row.ai_bucket] = row.total_samples
        by_language[lang]["sample_size"] += row.total_samples

    return list(by_language.values())


async def _get_archetype_distribution(
    db: AsyncSession, start_date: date
) -> list[dict]:
    """Get developer archetype distribution."""
    stmt = (
        select(
            AIUsageBucket.archetype,
            func.sum(AIUsageBucket.sample_size).label("count"),
        )
        .where(
            AIUsageBucket.date >= start_date,
            AIUsageBucket.archetype.isnot(None),
        )
        .group_by(AIUsageBucket.archetype)
        .order_by(func.sum(AIUsageBucket.sample_size).desc())
    )

    result = await db.execute(stmt)
    return [{"archetype": row.archetype, "count": row.count} for row in result.all()]


async def _get_model_popularity(db: AsyncSession, start_date: date) -> list[dict]:
    """Get AI model provider popularity from trend snapshots."""
    stmt = (
        select(TrendSnapshot.metric_value)
        .where(
            TrendSnapshot.date >= start_date,
            TrendSnapshot.metric_name == "model_popularity",
        )
        .order_by(TrendSnapshot.date.desc())
        .limit(1)
    )

    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row:
        return row if isinstance(row, list) else [row]
    return []


async def _get_generation_trends(db: AsyncSession, start_date: date) -> list[dict]:
    """Get generation volume trends."""
    stmt = (
        select(TrendSnapshot.date, TrendSnapshot.metric_value)
        .where(
            TrendSnapshot.date >= start_date,
            TrendSnapshot.metric_name == "daily_generations",
        )
        .order_by(TrendSnapshot.date)
    )

    result = await db.execute(stmt)
    return [
        {"date": str(row.date), "data": row.metric_value}
        for row in result.all()
    ]

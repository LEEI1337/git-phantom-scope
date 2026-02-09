"""Anonymous analytics pipeline for scoring data.

Persists anonymous, aggregated scoring results to PostgreSQL.
All data is bucketed and anonymized - NO PII is ever stored.

PRIVACY RULES:
- NO usernames, emails, or profile URLs
- NO GitHub tokens or API keys
- Only aggregated bucket data (language, archetype, AI bucket)
- Each record represents one anonymous analysis event
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from db.models import AIUsageBucket, GenerationStat, TrendSnapshot

logger = get_logger(__name__)


class AnalyticsPipeline:
    """Writes anonymous analytics data to PostgreSQL.

    Takes scoring results and persists only non-identifying,
    aggregated metrics for trend analysis and insights.
    """

    async def record_analysis(
        self,
        session: AsyncSession,
        scoring_result: dict[str, Any],
    ) -> None:
        """Record an anonymous analysis event.

        Args:
            session: Async SQLAlchemy session
            scoring_result: Output from ScoringEngine.score_profile()

        Creates:
            - AIUsageBucket record per primary language
            - TrendSnapshot with score distribution
        """
        try:
            scores = scoring_result.get("scores", {})
            archetype = scoring_result.get("archetype", {})
            ai_analysis = scoring_result.get("ai_analysis", {})
            tech_profile = scoring_result.get("tech_profile", {})

            today = date.today()
            bucket = ai_analysis.get("overall_bucket", "0_10")
            archetype_id = archetype.get("id", "unknown")

            # Record AI usage bucket per primary language
            languages = tech_profile.get("languages", [])
            primary_lang = languages[0] if languages else "unknown"

            ai_bucket = AIUsageBucket(
                date=today,
                language=primary_lang,
                ai_bucket=bucket,
                sample_size=1,
                archetype=archetype_id,
            )
            session.add(ai_bucket)

            # Record score distribution snapshot
            snapshot = TrendSnapshot(
                date=today,
                metric_name="score_distribution",
                metric_value={
                    "activity": scores.get("activity", 0),
                    "collaboration": scores.get("collaboration", 0),
                    "stack_diversity": scores.get("stack_diversity", 0),
                    "ai_savviness": scores.get("ai_savviness", 0),
                    "archetype": archetype_id,
                    "ai_bucket": bucket,
                },
                granularity="daily",
            )
            session.add(snapshot)

            logger.info(
                "analytics_recorded",
                archetype=archetype_id,
                ai_bucket=bucket,
                primary_lang=primary_lang,
            )

        except Exception:
            logger.exception("analytics_recording_failed")
            # Analytics failures must never break the main flow

    async def record_generation(
        self,
        session: AsyncSession,
        template_id: str,
        model_provider: str | None = None,
        model_name: str | None = None,
        tier: str = "free",
        duration_ms: int | None = None,
        success: bool = True,
        error_code: str | None = None,
    ) -> None:
        """Record an image generation event.

        Args:
            session: Async SQLAlchemy session
            template_id: Which template was used
            model_provider: AI model provider (gemini, openai, etc.)
            model_name: Specific model name
            tier: User tier (free, pro, enterprise)
            duration_ms: Generation time in milliseconds
            success: Whether generation succeeded
            error_code: Error code if failed
        """
        try:
            stat = GenerationStat(
                template_id=template_id,
                model_provider=model_provider,
                model_name=model_name,
                tier=tier,
                duration_ms=duration_ms,
                success=success,
                error_code=error_code,
            )
            session.add(stat)

            logger.info(
                "generation_recorded",
                template=template_id,
                provider=model_provider,
                success=success,
            )

        except Exception:
            logger.exception("generation_recording_failed")

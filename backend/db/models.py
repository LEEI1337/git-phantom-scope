"""Database models for anonymous analytics.

CRITICAL PRIVACY RULE:
These models store ONLY anonymous, aggregated data.
NO GitHub usernames, emails, profile data, or any PII is stored.
NO API keys or secrets are stored.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class GenerationStat(Base):
    """Tracks individual generation events (anonymous).

    Records which templates, models, and tiers are used
    for performance monitoring and business analytics.
    NO user-identifying information is stored.
    """

    __tablename__ = "generation_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    template_id: Mapped[str | None] = mapped_column(String(50))
    model_provider: Mapped[str | None] = mapped_column(String(50))
    model_name: Mapped[str | None] = mapped_column(String(100))
    tier: Mapped[str] = mapped_column(String(20), default="free")
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_code: Mapped[str | None] = mapped_column(String(50))

    def __repr__(self) -> str:
        return f"<GenerationStat(id={self.id}, template={self.template_id}, success={self.success})>"


class AIUsageBucket(Base):
    """Aggregated AI usage statistics by language.

    Stores anonymized, bucketed data about AI tool usage
    across different programming languages. Used for trend analysis.
    """

    __tablename__ = "ai_usage_buckets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ai_bucket: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 0_10, 10_30, 30_60, 60_100
    sample_size: Mapped[int] = mapped_column(Integer, default=1)
    archetype: Mapped[str | None] = mapped_column(String(50))

    def __repr__(self) -> str:
        return f"<AIUsageBucket(date={self.date}, lang={self.language}, bucket={self.ai_bucket})>"


class TrendSnapshot(Base):
    """Pre-aggregated trend metrics for the insights dashboard.

    Stores daily/weekly/monthly summaries of platform trends.
    All data is anonymous and aggregated.
    """

    __tablename__ = "trend_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    granularity: Mapped[str] = mapped_column(
        String(20), default="daily"
    )  # daily, weekly, monthly

    def __repr__(self) -> str:
        return f"<TrendSnapshot(date={self.date}, metric={self.metric_name})>"


class TemplateUsage(Base):
    """Tracks template popularity (anonymous).

    Helps prioritize template development and understand user preferences
    without tracking individual users.
    """

    __tablename__ = "template_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(20), default="free")
    count: Mapped[int] = mapped_column(Integer, default=1)

    def __repr__(self) -> str:
        return f"<TemplateUsage(date={self.date}, template={self.template_id}, count={self.count})>"

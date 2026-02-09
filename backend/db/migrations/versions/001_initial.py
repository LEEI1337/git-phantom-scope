"""001 create analytics tables

Revision ID: 001_initial
Revises: None
Create Date: 2025-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # generation_stats - Anonymous generation analytics
    op.create_table(
        "generation_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("archetype", sa.String(64), nullable=False, index=True),
        sa.Column("template_used", sa.String(64), nullable=False),
        sa.Column("model_provider", sa.String(32), nullable=False),
        sa.Column("generation_time_ms", sa.Integer(), nullable=False),
        sa.Column("output_format", sa.String(16), nullable=False),
        sa.Column("was_cached", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ai_usage_buckets - Aggregated AI usage trends
    op.create_table(
        "ai_usage_buckets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bucket_date", sa.Date(), nullable=False, index=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("request_count", sa.Integer(), server_default="0"),
        sa.Column("avg_latency_ms", sa.Float()),
        sa.Column("error_count", sa.Integer(), server_default="0"),
    )
    op.create_index(
        "ix_ai_usage_date_provider",
        "ai_usage_buckets",
        ["bucket_date", "provider"],
        unique=True,
    )

    # trend_snapshots - Daily archetype trends
    op.create_table(
        "trend_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("archetype", sa.String(64), nullable=False),
        sa.Column("count", sa.Integer(), server_default="0"),
        sa.Column("avg_activity", sa.Float()),
        sa.Column("avg_collaboration", sa.Float()),
        sa.Column("avg_diversity", sa.Float()),
        sa.Column("avg_ai_savviness", sa.Float()),
    )
    op.create_index(
        "ix_trend_date_archetype",
        "trend_snapshots",
        ["snapshot_date", "archetype"],
        unique=True,
    )

    # template_usage - Template popularity tracking
    op.create_table(
        "template_usage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("template_name", sa.String(64), nullable=False, index=True),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("use_count", sa.Integer(), server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("template_usage")
    op.drop_table("trend_snapshots")
    op.drop_table("ai_usage_buckets")
    op.drop_table("generation_stats")

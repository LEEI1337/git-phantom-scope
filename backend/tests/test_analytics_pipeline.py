"""Tests for the analytics pipeline service."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.analytics_pipeline import AnalyticsPipeline


@pytest.fixture
def pipeline():
    return AnalyticsPipeline()


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def sample_scoring_result():
    return {
        "scores": {
            "activity": 75,
            "collaboration": 30,
            "stack_diversity": 55,
            "ai_savviness": 60,
        },
        "archetype": {
            "id": "ai_indie_hacker",
            "name": "AI-Driven Indie Hacker",
            "description": "High AI usage",
            "confidence": 0.85,
            "alternatives": [],
        },
        "ai_analysis": {
            "overall_bucket": "60_100",
            "detected_tools": ["GitHub Copilot"],
            "confidence": "high",
            "ai_score": 60,
        },
        "tech_profile": {
            "languages": ["Python", "TypeScript"],
            "frameworks": ["fastapi", "react"],
            "top_repos": [],
            "primary_ecosystem": "full-stack",
        },
    }


class TestAnalyticsPipeline:
    """Test suite for AnalyticsPipeline."""

    @pytest.mark.asyncio
    async def test_record_analysis_creates_bucket(
        self, pipeline, mock_session, sample_scoring_result
    ):
        """record_analysis creates AIUsageBucket record."""
        await pipeline.record_analysis(mock_session, sample_scoring_result)
        # Should add AIUsageBucket + TrendSnapshot = 2 calls
        assert mock_session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_record_analysis_bucket_values(
        self, pipeline, mock_session, sample_scoring_result
    ):
        """AIUsageBucket has correct field values."""
        await pipeline.record_analysis(mock_session, sample_scoring_result)
        bucket = mock_session.add.call_args_list[0][0][0]
        assert bucket.language == "Python"
        assert bucket.ai_bucket == "60_100"
        assert bucket.archetype == "ai_indie_hacker"
        assert bucket.sample_size == 1
        assert bucket.date == date.today()

    @pytest.mark.asyncio
    async def test_record_analysis_snapshot_values(
        self, pipeline, mock_session, sample_scoring_result
    ):
        """TrendSnapshot has correct metric values."""
        await pipeline.record_analysis(mock_session, sample_scoring_result)
        snapshot = mock_session.add.call_args_list[1][0][0]
        assert snapshot.metric_name == "score_distribution"
        assert snapshot.granularity == "daily"
        assert snapshot.metric_value["activity"] == 75
        assert snapshot.metric_value["archetype"] == "ai_indie_hacker"

    @pytest.mark.asyncio
    async def test_record_analysis_no_languages(self, pipeline, mock_session):
        """Handles missing languages gracefully."""
        result = {
            "scores": {"activity": 0, "collaboration": 0, "stack_diversity": 0, "ai_savviness": 0},
            "archetype": {"id": "code_explorer"},
            "ai_analysis": {"overall_bucket": "0_10"},
            "tech_profile": {"languages": []},
        }
        await pipeline.record_analysis(mock_session, result)
        bucket = mock_session.add.call_args_list[0][0][0]
        assert bucket.language == "unknown"

    @pytest.mark.asyncio
    async def test_record_analysis_error_swallowed(self, pipeline, mock_session):
        """Analytics errors never propagate to caller."""
        mock_session.add.side_effect = Exception("DB down")
        # Should not raise
        await pipeline.record_analysis(mock_session, {})

    @pytest.mark.asyncio
    async def test_record_generation(self, pipeline, mock_session):
        """record_generation creates GenerationStat."""
        await pipeline.record_generation(
            mock_session,
            template_id="portfolio_banner",
            model_provider="gemini",
            model_name="gemini-2.0-flash",
            tier="free",
            duration_ms=1500,
            success=True,
        )
        assert mock_session.add.call_count == 1
        stat = mock_session.add.call_args[0][0]
        assert stat.template_id == "portfolio_banner"
        assert stat.model_provider == "gemini"
        assert stat.success is True

    @pytest.mark.asyncio
    async def test_record_generation_failure(self, pipeline, mock_session):
        """Failed generation recorded with error code."""
        await pipeline.record_generation(
            mock_session,
            template_id="skill_wheel",
            success=False,
            error_code="MODEL_TIMEOUT",
        )
        stat = mock_session.add.call_args[0][0]
        assert stat.success is False
        assert stat.error_code == "MODEL_TIMEOUT"

    @pytest.mark.asyncio
    async def test_record_generation_error_swallowed(self, pipeline, mock_session):
        """Generation recording errors never propagate."""
        mock_session.add.side_effect = Exception("DB down")
        await pipeline.record_generation(mock_session, template_id="test")

"""Tests for Team/Org Analytics Dashboard Service."""

import fakeredis.aioredis
import pytest

from services.team_analytics import (
    AggregationPeriod,
    TeamAnalyticsService,
    TeamDashboard,
    TeamError,
    TeamMemberSummary,
)


@pytest.fixture
async def fake_redis():
    server = fakeredis.FakeServer()
    redis = fakeredis.aioredis.FakeRedis(server=server)
    yield redis
    await redis.close()


@pytest.fixture
def service(fake_redis):
    return TeamAnalyticsService(fake_redis)


def _make_member(
    member_hash: str,
    activity: float = 70,
    collaboration: float = 60,
    archetype: str = "code_explorer",
    ai_tools: list[str] | None = None,
    languages: list[str] | None = None,
) -> TeamMemberSummary:
    return TeamMemberSummary(
        member_hash=member_hash,
        scores={
            "activity": activity,
            "collaboration": collaboration,
            "stack_diversity": 50.0,
            "ai_savviness": 40.0,
        },
        archetype=archetype,
        ai_tools_detected=ai_tools or [],
        top_languages=languages or ["Python"],
    )


# --- Model Tests ---


class TestTeamMemberSummary:
    def test_create(self):
        m = _make_member("hash123")
        assert m.member_hash == "hash123"
        assert m.scores["activity"] == 70
        assert m.archetype == "code_explorer"
        assert m.analyzed_at != ""

    def test_defaults(self):
        m = TeamMemberSummary(member_hash="abc")
        assert m.archetype == "code_explorer"
        assert m.ai_tools_detected == []
        assert m.top_languages == []


class TestTeamDashboard:
    def test_empty_dashboard(self):
        d = TeamDashboard(org_id="test")
        assert d.team_size == 0
        assert d.ai_adoption_rate == 0.0
        assert d.period == "30d"

    def test_serialization(self):
        d = TeamDashboard(org_id="org", team_size=5)
        data = d.model_dump(mode="json")
        assert data["org_id"] == "org"
        assert data["team_size"] == 5


class TestAggregationPeriod:
    def test_values(self):
        assert AggregationPeriod.WEEK.value == "7d"
        assert AggregationPeriod.MONTH.value == "30d"
        assert AggregationPeriod.QUARTER.value == "90d"
        assert AggregationPeriod.YEAR.value == "1y"


# --- Service Tests ---


class TestTeamAnalyticsService:
    @pytest.mark.asyncio
    async def test_add_member(self, service):
        member = _make_member("hash1")
        result = await service.add_member_analysis("acme", member)
        assert result == "hash1"

    @pytest.mark.asyncio
    async def test_dashboard_empty_org(self, service):
        dashboard = await service.get_dashboard("empty-org")
        assert dashboard.team_size == 0
        assert dashboard.aggregate_scores == {}

    @pytest.mark.asyncio
    async def test_dashboard_single_member(self, service):
        member = _make_member(
            "hash1",
            activity=80,
            collaboration=60,
            archetype="backend_architect",
            ai_tools=["copilot"],
            languages=["Python", "Go"],
        )
        await service.add_member_analysis("org1", member)

        dashboard = await service.get_dashboard("org1")
        assert dashboard.team_size == 1
        assert dashboard.aggregate_scores["activity"] == 80.0
        assert dashboard.archetype_distribution == {"backend_architect": 1}
        assert dashboard.ai_adoption_rate == 100.0
        assert any(l["language"] == "Python" for l in dashboard.top_languages)

    @pytest.mark.asyncio
    async def test_dashboard_multiple_members(self, service):
        m1 = _make_member(
            "hash1",
            activity=80,
            collaboration=60,
            archetype="backend_architect",
            ai_tools=["copilot"],
            languages=["Python"],
        )
        m2 = _make_member(
            "hash2",
            activity=60,
            collaboration=80,
            archetype="full_stack_polyglot",
            ai_tools=["cursor"],
            languages=["TypeScript", "Python"],
        )
        m3 = _make_member(
            "hash3",
            activity=90,
            collaboration=70,
            archetype="backend_architect",
            ai_tools=[],
            languages=["Go"],
        )
        await service.add_member_analysis("org2", m1)
        await service.add_member_analysis("org2", m2)
        await service.add_member_analysis("org2", m3)

        dashboard = await service.get_dashboard("org2")
        assert dashboard.team_size == 3
        # Average activity: (80+60+90)/3 ≈ 76.7
        assert 76 <= dashboard.aggregate_scores["activity"] <= 77
        assert dashboard.archetype_distribution["backend_architect"] == 2
        assert dashboard.archetype_distribution["full_stack_polyglot"] == 1
        # 2 out of 3 members have AI tools
        assert dashboard.ai_adoption_rate == pytest.approx(66.7, abs=0.1)
        assert dashboard.ai_tools_usage["copilot"] == 1
        assert dashboard.ai_tools_usage["cursor"] == 1

    @pytest.mark.asyncio
    async def test_dashboard_periods(self, service):
        member = _make_member("hash1")
        await service.add_member_analysis("org3", member)

        for period in AggregationPeriod:
            dashboard = await service.get_dashboard("org3", period)
            assert dashboard.period == period.value

    @pytest.mark.asyncio
    async def test_team_comparison(self, service):
        m1 = _make_member("hash1", activity=80, archetype="backend_architect")
        m2 = _make_member("hash2", activity=60, archetype="data_scientist")
        await service.add_member_analysis("org4", m1)
        await service.add_member_analysis("org4", m2)

        comparison = await service.get_team_comparison("org4")
        assert len(comparison) == 2
        ids = {c["id"] for c in comparison}
        assert "hash1"[:8] in ids
        assert "hash2"[:8] in ids

    @pytest.mark.asyncio
    async def test_comparison_empty(self, service):
        comparison = await service.get_team_comparison("empty")
        assert comparison == []

    @pytest.mark.asyncio
    async def test_remove_member(self, service):
        member = _make_member("hash_rm")
        await service.add_member_analysis("org5", member)

        dashboard = await service.get_dashboard("org5")
        assert dashboard.team_size == 1

        removed = await service.remove_member("org5", "hash_rm")
        assert removed is True

    @pytest.mark.asyncio
    async def test_remove_nonexistent(self, service):
        removed = await service.remove_member("org5", "nonexistent")
        assert removed is False

    @pytest.mark.asyncio
    async def test_clear_team(self, service):
        m1 = _make_member("hash_a")
        m2 = _make_member("hash_b")
        await service.add_member_analysis("org6", m1)
        await service.add_member_analysis("org6", m2)

        deleted = await service.clear_team("org6")
        assert deleted == 2

        dashboard = await service.get_dashboard("org6")
        assert dashboard.team_size == 0

    @pytest.mark.asyncio
    async def test_clear_empty_team(self, service):
        deleted = await service.clear_team("nonexistent")
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_top_languages_sorted(self, service):
        m1 = _make_member("h1", languages=["Python", "Go"])
        m2 = _make_member("h2", languages=["Python", "Rust"])
        m3 = _make_member("h3", languages=["Python", "Go", "Rust"])
        await service.add_member_analysis("org7", m1)
        await service.add_member_analysis("org7", m2)
        await service.add_member_analysis("org7", m3)

        dashboard = await service.get_dashboard("org7")
        assert dashboard.top_languages[0]["language"] == "Python"
        assert dashboard.top_languages[0]["count"] == 3


# --- Error class ---


class TestTeamError:
    def test_defaults(self):
        err = TeamError()
        assert err.code == "TEAM_ERROR"
        assert err.status_code == 400

    def test_custom_message(self):
        err = TeamError("Team not found")
        assert err.message == "Team not found"

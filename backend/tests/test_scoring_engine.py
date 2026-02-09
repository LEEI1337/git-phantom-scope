"""Tests for the scoring engine."""

import pytest

from services.scoring_engine import ScoringEngine


class TestScoringEngine:
    """Test suite for ScoringEngine."""

    def setup_method(self):
        self.engine = ScoringEngine()

    def test_activity_score_active_user(self):
        """Active user with many recent commits gets high activity score."""
        profile = {
            "public_repos": 30,
            "created_at": "2020-01-01T00:00:00Z",
        }
        repos = [
            {"name": f"repo-{i}", "stargazers_count": 5, "forks_count": 1}
            for i in range(30)
        ]
        events = [
            {"type": "PushEvent", "created_at": "2025-08-15T12:00:00Z"}
            for _ in range(50)
        ]
        scores = self.engine.calculate_scores(profile, repos, events)
        assert scores["activity"] >= 60
        assert 0 <= scores["activity"] <= 100

    def test_collaboration_score_with_prs(self):
        """User with PR events gets collaboration score."""
        profile = {"public_repos": 10, "created_at": "2022-01-01T00:00:00Z"}
        repos = [
            {"name": "repo", "stargazers_count": 0, "forks_count": 5}
        ]
        events = [
            {"type": "PullRequestEvent", "created_at": "2025-08-01T12:00:00Z"},
            {"type": "PullRequestReviewEvent", "created_at": "2025-08-02T12:00:00Z"},
            {"type": "IssuesEvent", "created_at": "2025-08-03T12:00:00Z"},
            {"type": "ForkEvent", "created_at": "2025-08-04T12:00:00Z"},
        ]
        scores = self.engine.calculate_scores(profile, repos, events)
        assert scores["collaboration"] > 0
        assert 0 <= scores["collaboration"] <= 100

    def test_stack_diversity_multiple_languages(self):
        """User with many languages gets high diversity score."""
        profile = {"public_repos": 10, "created_at": "2022-01-01T00:00:00Z"}
        repos = [
            {"name": "py-repo", "language": "Python", "stargazers_count": 5, "forks_count": 0},
            {"name": "ts-repo", "language": "TypeScript", "stargazers_count": 3, "forks_count": 0},
            {"name": "go-repo", "language": "Go", "stargazers_count": 2, "forks_count": 0},
            {"name": "rs-repo", "language": "Rust", "stargazers_count": 1, "forks_count": 0},
            {"name": "java-repo", "language": "Java", "stargazers_count": 1, "forks_count": 0},
        ]
        events = []
        scores = self.engine.calculate_scores(profile, repos, events)
        assert scores["stack_diversity"] >= 40

    def test_ai_savviness_zero_without_signals(self):
        """User without AI signals gets low AI score."""
        profile = {"public_repos": 5, "created_at": "2023-01-01T00:00:00Z"}
        repos = [
            {"name": "simple-repo", "language": "JavaScript", "stargazers_count": 0, "forks_count": 0},
        ]
        events = [{"type": "PushEvent", "created_at": "2025-08-01T12:00:00Z"}]
        scores = self.engine.calculate_scores(profile, repos, events)
        assert scores["ai_savviness"] <= 30

    def test_all_scores_within_range(self):
        """All scores should be between 0 and 100."""
        profile = {"public_repos": 0, "created_at": "2025-01-01T00:00:00Z"}
        scores = self.engine.calculate_scores(profile, [], [])
        for dimension, value in scores.items():
            assert 0 <= value <= 100, f"{dimension} out of range: {value}"

    def test_archetype_classification(self):
        """Scores should map to a valid archetype."""
        scores = {
            "activity": 80,
            "collaboration": 20,
            "stack_diversity": 60,
            "ai_savviness": 90,
        }
        archetype = self.engine.classify_archetype(scores)
        assert archetype is not None
        assert isinstance(archetype, str)
        assert len(archetype) > 0

    def test_archetype_ai_indie_hacker(self):
        """High AI + High Activity + Low Collab = AI-Driven Indie Hacker."""
        scores = {
            "activity": 85,
            "collaboration": 15,
            "stack_diversity": 50,
            "ai_savviness": 90,
        }
        archetype = self.engine.classify_archetype(scores)
        assert archetype == "AI-Driven Indie Hacker"

    def test_archetype_open_source_maintainer(self):
        """High Collab + High Activity = Open Source Maintainer."""
        scores = {
            "activity": 80,
            "collaboration": 85,
            "stack_diversity": 50,
            "ai_savviness": 30,
        }
        archetype = self.engine.classify_archetype(scores)
        assert archetype == "Open Source Maintainer"

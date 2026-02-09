"""Tests for the scoring engine."""

from services.scoring_engine import ScoringEngine


class TestScoringEngine:
    """Test suite for ScoringEngine."""

    def setup_method(self):
        self.engine = ScoringEngine()

    def _make_profile(self, **overrides) -> dict:
        """Create a base profile dict with optional overrides."""
        profile = {
            "username": "testuser",
            "public_repos": 10,
            "followers": 20,
            "following": 10,
            "created_at": "2022-01-01T00:00:00Z",
            "repos": [],
            "languages": [],
            "contribution_stats": {
                "recent_commits": 0,
                "recent_prs": 0,
                "recent_issues": 0,
                "recent_reviews": 0,
                "total_events": 0,
                "period": "last_90_days",
            },
            "pinned_repos": [],
            "organizations": [],
            "contribution_calendar": [],
        }
        profile.update(overrides)
        return profile

    def test_activity_score_active_user(self):
        """Active user with many recent commits gets high activity score."""
        profile = self._make_profile(
            repos=[
                {
                    "name": f"repo-{i}",
                    "stars": 5,
                    "forks": 1,
                    "updated_at": "2026-01-15T12:00:00Z",
                    "topics": [],
                }
                for i in range(30)
            ],
            contribution_stats={
                "recent_commits": 80,
                "recent_prs": 5,
                "recent_issues": 3,
                "recent_reviews": 2,
                "total_events": 90,
                "period": "last_90_days",
            },
        )
        result = self.engine.score_profile(profile)
        assert result["scores"]["activity"] >= 40
        assert 0 <= result["scores"]["activity"] <= 100

    def test_collaboration_score_with_prs(self):
        """User with PR events gets collaboration score."""
        profile = self._make_profile(
            followers=30,
            repos=[
                {
                    "name": "repo",
                    "stars": 0,
                    "forks": 10,
                    "updated_at": "2026-01-01T00:00:00Z",
                    "topics": [],
                },
            ],
            contribution_stats={
                "recent_commits": 5,
                "recent_prs": 8,
                "recent_issues": 5,
                "recent_reviews": 3,
                "total_events": 20,
                "period": "last_90_days",
            },
        )
        result = self.engine.score_profile(profile)
        assert result["scores"]["collaboration"] > 0
        assert 0 <= result["scores"]["collaboration"] <= 100

    def test_stack_diversity_multiple_languages(self):
        """User with many languages gets high diversity score."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "py-repo",
                    "language": "Python",
                    "stars": 5,
                    "forks": 0,
                    "topics": ["python"],
                    "updated_at": "2026-01-01",
                },
                {
                    "name": "ts-repo",
                    "language": "TypeScript",
                    "stars": 3,
                    "forks": 0,
                    "topics": ["typescript"],
                    "updated_at": "2026-01-01",
                },
                {
                    "name": "go-repo",
                    "language": "Go",
                    "stars": 2,
                    "forks": 0,
                    "topics": ["golang"],
                    "updated_at": "2026-01-01",
                },
                {
                    "name": "rs-repo",
                    "language": "Rust",
                    "stars": 1,
                    "forks": 0,
                    "topics": ["rust"],
                    "updated_at": "2026-01-01",
                },
                {
                    "name": "java-repo",
                    "language": "Java",
                    "stars": 1,
                    "forks": 0,
                    "topics": ["java"],
                    "updated_at": "2026-01-01",
                },
            ],
            languages=[
                {"name": "Python", "count": 1, "percentage": 20.0},
                {"name": "TypeScript", "count": 1, "percentage": 20.0},
                {"name": "Go", "count": 1, "percentage": 20.0},
                {"name": "Rust", "count": 1, "percentage": 20.0},
                {"name": "Java", "count": 1, "percentage": 20.0},
            ],
        )
        result = self.engine.score_profile(profile)
        assert result["scores"]["stack_diversity"] >= 40

    def test_ai_savviness_with_commit_data(self):
        """AI savviness score increases with commit-level AI signals."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "ai-project",
                    "language": "Python",
                    "stars": 5,
                    "forks": 0,
                    "topics": ["machine-learning", "copilot"],
                    "description": "ML model",
                    "updated_at": "2026-01-01",
                },
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
        )
        commits = [
            {"message": "feat: implement model with Copilot suggestions"},
            {
                "message": "fix: resolve training loop\n\nCo-authored-by: copilot-chat[bot] <copilot@github.com>"
            },
            {"message": "docs: add README for AI project"},
        ]
        result = self.engine.score_profile(profile, commits)
        assert result["scores"]["ai_savviness"] > 0
        assert result["ai_analysis"]["confidence"] == "high"

    def test_ai_savviness_zero_without_signals(self):
        """User without AI signals gets low AI score."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "simple-repo",
                    "language": "JavaScript",
                    "stars": 0,
                    "forks": 0,
                    "topics": [],
                    "updated_at": "2026-01-01",
                },
            ],
            languages=[{"name": "JavaScript", "count": 1, "percentage": 100.0}],
        )
        result = self.engine.score_profile(profile)
        assert result["scores"]["ai_savviness"] <= 30

    def test_all_scores_within_range(self):
        """All scores should be between 0 and 100."""
        profile = self._make_profile()
        result = self.engine.score_profile(profile)
        for dimension, value in result["scores"].items():
            assert 0 <= value <= 100, f"{dimension} out of range: {value}"

    def test_archetype_classification(self):
        """Score profile returns a valid archetype dict."""
        profile = self._make_profile(
            repos=[
                {
                    "name": f"repo-{i}",
                    "language": "Python",
                    "stars": 5,
                    "forks": 1,
                    "topics": ["ai"],
                    "updated_at": "2026-01-01",
                }
                for i in range(10)
            ],
            languages=[{"name": "Python", "count": 10, "percentage": 100.0}],
            contribution_stats={
                "recent_commits": 50,
                "recent_prs": 10,
                "recent_issues": 5,
                "recent_reviews": 5,
                "total_events": 70,
                "period": "last_90_days",
            },
        )
        result = self.engine.score_profile(profile)
        archetype = result["archetype"]
        assert "id" in archetype
        assert "name" in archetype
        assert "description" in archetype
        assert len(archetype["name"]) > 0

    def test_archetype_ai_indie_hacker(self):
        """High AI + High Activity + Low Collab = AI-Driven Indie Hacker."""
        profile = self._make_profile(
            repos=[
                {
                    "name": f"ai-tool-{i}",
                    "language": "Python",
                    "stars": 10,
                    "forks": 0,
                    "description": "AI model training pipeline",
                    "topics": ["machine-learning", "copilot", "generative-ai", "llm", "ai"],
                    "updated_at": "2026-01-01",
                }
                for i in range(15)
            ],
            languages=[
                {"name": "Python", "count": 10, "percentage": 70.0},
                {"name": "Jupyter Notebook", "count": 3, "percentage": 20.0},
                {"name": "R", "count": 1, "percentage": 10.0},
            ],
            contribution_stats={
                "recent_commits": 80,
                "recent_prs": 0,
                "recent_issues": 0,
                "recent_reviews": 0,
                "total_events": 80,
                "period": "last_90_days",
            },
            followers=5,
        )
        # Also provide strong AI commit signals
        commits = [
            {"message": "feat: train model with Copilot"},
            {"message": "feat: AI-generated data pipeline"},
            {"message": "feat: implement with ChatGPT suggestions"},
        ] * 5
        result = self.engine.score_profile(profile, commits)
        assert result["archetype"]["id"] == "ai_indie_hacker"

    def test_archetype_open_source_maintainer(self):
        """High Collab + High Activity = Open Source Maintainer."""
        profile = self._make_profile(
            followers=60,
            repos=[
                {
                    "name": f"oss-{i}",
                    "language": "Go",
                    "stars": 20,
                    "forks": 15,
                    "topics": ["open-source"],
                    "updated_at": "2026-01-01",
                }
                for i in range(20)
            ],
            languages=[{"name": "Go", "count": 20, "percentage": 100.0}],
            contribution_stats={
                "recent_commits": 100,
                "recent_prs": 15,
                "recent_issues": 12,
                "recent_reviews": 8,
                "total_events": 135,
                "period": "last_90_days",
            },
        )
        result = self.engine.score_profile(profile)
        assert result["archetype"]["id"] == "open_source_maintainer"

    def test_tech_profile_built(self):
        """Tech profile includes languages, frameworks, and top repos."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "web-app",
                    "language": "TypeScript",
                    "stars": 50,
                    "forks": 10,
                    "description": "A web application",
                    "topics": ["react", "nextjs", "tailwindcss"],
                    "updated_at": "2026-01-01",
                },
            ],
            languages=[{"name": "TypeScript", "count": 1, "percentage": 100.0}],
        )
        result = self.engine.score_profile(profile)
        tech = result["tech_profile"]
        assert "languages" in tech
        assert "frameworks" in tech
        assert "top_repos" in tech
        assert "react" in tech["frameworks"]

    def test_score_profile_with_no_commits(self):
        """Score profile works correctly without commit data."""
        profile = self._make_profile()
        result = self.engine.score_profile(profile)
        assert "scores" in result
        assert "archetype" in result
        assert "ai_analysis" in result
        assert "tech_profile" in result

    def test_ai_analysis_with_commit_details(self):
        """AI analysis includes commit analysis details when available."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "test",
                    "language": "Python",
                    "stars": 0,
                    "forks": 0,
                    "topics": [],
                    "updated_at": "2026-01-01",
                },
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
        )
        commits = [
            {"message": "feat: build auth with Copilot"},
            {"message": "chore: update deps"},
        ]
        result = self.engine.score_profile(profile, commits)
        ai = result["ai_analysis"]
        assert "commit_analysis" in ai
        assert ai["commit_analysis"]["commits_analyzed"] == 2
        assert ai["confidence"] == "high"

    def test_fallback_archetype(self):
        """Minimal profile gets fallback archetype."""
        profile = self._make_profile()
        result = self.engine.score_profile(profile)
        assert result["archetype"]["id"] is not None

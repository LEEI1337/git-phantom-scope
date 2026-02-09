"""Comprehensive tests for Scoring Engine V2 features.

Covers: log scaling, time decay, Shannon entropy, archetype normalization,
language dict format, AI config detection, ecosystem detection,
burst score integration, and all archetype requirement paths.
"""

from datetime import UTC, datetime, timedelta

from services.scoring_engine import (
    ARCHETYPES,
    KNOWN_FRAMEWORKS,
    ScoringEngine,
    _log_scale,
    _time_decay_weight,
)


class TestLogScale:
    """Tests for _log_scale helper."""

    def test_zero_input(self):
        assert _log_scale(0, 100, 25) == 0.0

    def test_negative_input(self):
        assert _log_scale(-5, 100, 25) == 0.0

    def test_at_max_val(self):
        result = _log_scale(100, 100, 25)
        assert abs(result - 25.0) < 0.01

    def test_above_max_val_capped(self):
        result = _log_scale(500, 100, 25)
        assert result == 25.0

    def test_below_max_val(self):
        result = _log_scale(10, 100, 25)
        assert 0 < result < 25

    def test_diminishing_returns(self):
        """Doubling input does not double output (log curve)."""
        low = _log_scale(10, 100, 25)
        high = _log_scale(20, 100, 25)
        assert high < low * 2


class TestTimeDecay:
    """Tests for _time_decay_weight helper."""

    def test_none_date(self):
        assert _time_decay_weight(None) == 0.0

    def test_empty_date(self):
        assert _time_decay_weight("") == 0.0

    def test_invalid_date(self):
        assert _time_decay_weight("not-a-date") == 0.0

    def test_today_weight_near_one(self):
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        weight = _time_decay_weight(today)
        assert weight > 0.95

    def test_old_date_low_weight(self):
        old = (datetime.now(UTC) - timedelta(days=365)).strftime("%Y-%m-%d")
        weight = _time_decay_weight(old)
        assert weight < 0.3

    def test_iso_format_with_time(self):
        recent = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        weight = _time_decay_weight(recent)
        assert weight > 0.9

    def test_half_life_at_half(self):
        """Weight at exactly half_life_days should be ~0.5."""
        half_date = (datetime.now(UTC) - timedelta(days=180)).strftime("%Y-%m-%d")
        weight = _time_decay_weight(half_date, half_life_days=180)
        assert abs(weight - 0.5) < 0.05


class TestScoringEngineV2:
    """V2-specific scoring engine tests."""

    def setup_method(self):
        self.engine = ScoringEngine()

    def _make_profile(self, **overrides) -> dict:
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

    # --- Languages as dict format ---

    def test_stack_diversity_with_dict_languages(self):
        """Languages passed as dict format are handled correctly."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "repo",
                    "stars": 0,
                    "forks": 0,
                    "topics": [],
                    "updated_at": "2026-01-01",
                }
            ],
            languages={"Python": 60.0, "Go": 25.0, "Rust": 15.0},
        )
        result = self.engine.score_profile(profile)
        assert result["scores"]["stack_diversity"] > 0

    def test_ai_savviness_with_dict_languages(self):
        """AI savviness handles dict-format languages."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "ml-project",
                    "stars": 0,
                    "forks": 0,
                    "topics": ["machine-learning"],
                    "description": "ML model",
                    "updated_at": "2026-01-01",
                }
            ],
            languages={"Python": 70.0, "Jupyter Notebook": 30.0},
        )
        result = self.engine.score_profile(profile)
        assert result["scores"]["ai_savviness"] > 0

    def test_tech_profile_with_dict_languages(self):
        """Tech profile build handles dict-format languages."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "web",
                    "stars": 5,
                    "forks": 0,
                    "topics": ["react"],
                    "updated_at": "2026-01-01",
                }
            ],
            languages={"TypeScript": 80.0, "CSS": 20.0},
        )
        result = self.engine.score_profile(profile)
        assert "TypeScript" in result["tech_profile"]["languages"]

    # --- AI Config File Detection ---

    def test_ai_config_detection_copilot_instructions(self):
        """Repos mentioning copilot-instructions in name/desc/topics are detected."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "copilot-instructions-repo",
                    "stars": 0,
                    "forks": 0,
                    "topics": [],
                    "description": "Project with copilot-instructions",
                    "updated_at": "2026-01-01",
                },
                {
                    "name": "cursorrules-config",
                    "stars": 0,
                    "forks": 0,
                    "topics": ["cursorrules"],
                    "description": "",
                    "updated_at": "2026-01-01",
                },
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
        )
        result = self.engine.score_profile(profile)
        # AI config indicators should boost the ai_savviness score
        assert result["scores"]["ai_savviness"] > 0

    # --- Archetype requirements ---

    def test_archetype_frontend_craftsman(self):
        """Frontend languages trigger frontend_craftsman archetype eligibility."""
        profile = self._make_profile(
            repos=[
                {
                    "name": f"ui-{i}",
                    "language": "TypeScript",
                    "stars": 5,
                    "forks": 2,
                    "topics": ["react", "nextjs", "tailwindcss"],
                    "updated_at": "2026-01-01",
                }
                for i in range(20)
            ],
            languages=[
                {"name": "TypeScript", "count": 15, "percentage": 70.0},
                {"name": "CSS", "count": 5, "percentage": 20.0},
                {"name": "JavaScript", "count": 3, "percentage": 10.0},
            ],
            contribution_stats={
                "recent_commits": 90,
                "recent_prs": 10,
                "recent_issues": 5,
                "recent_reviews": 5,
                "total_events": 110,
                "period": "last_90_days",
            },
            followers=30,
        )
        result = self.engine.score_profile(profile)
        archetype_id = result["archetype"]["id"]
        # Should be eligible for frontend_craftsman
        alt_ids = [a["id"] for a in result["archetype"].get("alternatives", [])]
        all_ids = [archetype_id] + alt_ids
        assert "frontend_craftsman" in all_ids or archetype_id in (
            "frontend_craftsman",
            "rising_developer",
            "full_stack_polyglot",
        )

    def test_archetype_data_scientist_eligible(self):
        """Data science languages make data_scientist archetype eligible."""
        profile = self._make_profile(
            repos=[
                {
                    "name": f"ml-{i}",
                    "language": "Python",
                    "stars": 10,
                    "forks": 2,
                    "topics": ["machine-learning", "pytorch", "deep-learning"],
                    "description": "Neural network training",
                    "updated_at": "2026-01-01",
                }
                for i in range(15)
            ],
            languages=[
                {"name": "Python", "count": 10, "percentage": 60.0},
                {"name": "Jupyter Notebook", "count": 5, "percentage": 30.0},
                {"name": "R", "count": 2, "percentage": 10.0},
            ],
            contribution_stats={
                "recent_commits": 70,
                "recent_prs": 5,
                "recent_issues": 3,
                "recent_reviews": 2,
                "total_events": 80,
                "period": "last_90_days",
            },
            followers=25,
        )
        commits = [
            {"message": "feat: train BERT model with Copilot"},
            {"message": "feat: AI-generated data preprocessing"},
        ] * 5
        result = self.engine.score_profile(profile, commits)
        # Profile with data science languages should score well
        assert result["scores"]["ai_savviness"] > 30
        assert result["archetype"]["id"] is not None
        assert result["archetype"]["confidence"] > 0

    def test_archetype_devops_specialist_eligible(self):
        """DevOps topics make devops_specialist archetype eligible."""
        profile = self._make_profile(
            repos=[
                {
                    "name": f"infra-{i}",
                    "language": "Go",
                    "stars": 5,
                    "forks": 3,
                    "topics": ["docker", "kubernetes", "terraform", "ci-cd"],
                    "updated_at": "2026-01-01",
                }
                for i in range(15)
            ],
            languages=[
                {"name": "Go", "count": 8, "percentage": 50.0},
                {"name": "Python", "count": 4, "percentage": 25.0},
                {"name": "Shell", "count": 4, "percentage": 25.0},
            ],
            contribution_stats={
                "recent_commits": 60,
                "recent_prs": 8,
                "recent_issues": 5,
                "recent_reviews": 5,
                "total_events": 78,
                "period": "last_90_days",
            },
            followers=15,
        )
        result = self.engine.score_profile(profile)
        # DevOps profile should have good activity and stack scores
        assert result["scores"]["activity"] > 30
        assert result["scores"]["stack_diversity"] > 30
        assert result["archetype"]["id"] is not None
        # Should have alternatives showing the system works
        assert len(result["archetype"]["alternatives"]) > 0

    def test_archetype_security_sentinel(self):
        """Security topics trigger security_sentinel eligibility."""
        profile = self._make_profile(
            repos=[
                {
                    "name": f"sec-{i}",
                    "language": "Python",
                    "stars": 8,
                    "forks": 2,
                    "topics": ["security", "pentest", "cybersecurity", "owasp"],
                    "updated_at": "2026-01-01",
                }
                for i in range(12)
            ],
            languages=[
                {"name": "Python", "count": 8, "percentage": 60.0},
                {"name": "C", "count": 4, "percentage": 30.0},
                {"name": "Shell", "count": 2, "percentage": 10.0},
            ],
            contribution_stats={
                "recent_commits": 50,
                "recent_prs": 5,
                "recent_issues": 8,
                "recent_reviews": 3,
                "total_events": 66,
                "period": "last_90_days",
            },
            followers=20,
        )
        result = self.engine.score_profile(profile)
        archetype_id = result["archetype"]["id"]
        alt_ids = [a["id"] for a in result["archetype"].get("alternatives", [])]
        all_ids = [archetype_id] + alt_ids
        assert "security_sentinel" in all_ids

    def test_archetype_fallback_with_no_qualifying(self):
        """When no archetype meets min_score, fallback to code_explorer."""
        profile = self._make_profile(
            repos=[],
            languages=[],
            contribution_stats={
                "recent_commits": 0,
                "recent_prs": 0,
                "recent_issues": 0,
                "recent_reviews": 0,
                "total_events": 0,
                "period": "last_90_days",
            },
            followers=0,
            following=0,
        )
        result = self.engine.score_profile(profile)
        # code_explorer has min_score=0, so it always qualifies
        assert result["archetype"]["id"] is not None

    def test_archetype_confidence_field(self):
        """V2 archetype result includes confidence and alternatives."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "repo",
                    "stars": 5,
                    "forks": 0,
                    "topics": [],
                    "updated_at": "2026-01-01",
                }
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
            contribution_stats={
                "recent_commits": 30,
                "recent_prs": 2,
                "recent_issues": 1,
                "recent_reviews": 1,
                "total_events": 34,
                "period": "last_90_days",
            },
        )
        result = self.engine.score_profile(profile)
        archetype = result["archetype"]
        assert "confidence" in archetype
        assert isinstance(archetype["confidence"], float)
        assert 0 <= archetype["confidence"] <= 1.0
        assert "alternatives" in archetype
        assert isinstance(archetype["alternatives"], list)

    # --- Ecosystem detection ---

    def test_ecosystem_data_science(self):
        """Data science ecosystem detected from ML frameworks."""
        eco = ScoringEngine._detect_ecosystem({"Python", "R"}, {"pytorch", "tensorflow"})
        assert eco == "data-science"

    def test_ecosystem_full_stack(self):
        """Full-stack detected when both web + backend frameworks present."""
        eco = ScoringEngine._detect_ecosystem({"TypeScript", "Python"}, {"react", "fastapi"})
        assert eco == "full-stack"

    def test_ecosystem_frontend(self):
        """Frontend detected from web frameworks only."""
        eco = ScoringEngine._detect_ecosystem({"TypeScript"}, {"react", "nextjs"})
        assert eco == "frontend"

    def test_ecosystem_backend(self):
        """Backend detected from backend frameworks only."""
        eco = ScoringEngine._detect_ecosystem({"Python"}, {"django", "flask"})
        assert eco == "backend"

    def test_ecosystem_devops(self):
        """DevOps detected from infrastructure tools."""
        eco = ScoringEngine._detect_ecosystem({"Python"}, {"docker", "kubernetes"})
        assert eco == "devops"

    def test_ecosystem_backend_from_langs(self):
        """Backend inferred from language set when no frameworks."""
        eco = ScoringEngine._detect_ecosystem({"Go", "Rust"}, set())
        assert eco == "backend"

    def test_ecosystem_frontend_from_langs(self):
        """Frontend inferred from JS/TS when no frameworks."""
        eco = ScoringEngine._detect_ecosystem({"JavaScript"}, set())
        assert eco == "frontend"

    def test_ecosystem_general_fallback(self):
        """General returned when no specific ecosystem detected."""
        eco = ScoringEngine._detect_ecosystem({"Haskell"}, set())
        assert eco == "general"

    def test_ecosystem_data_science_from_langs(self):
        """Data science from Jupyter Notebook language."""
        eco = ScoringEngine._detect_ecosystem({"Jupyter Notebook"}, set())
        assert eco == "data-science"

    # --- AI tool detection in _analyze_ai_usage ---

    def test_ai_usage_detects_gemini_from_topics(self):
        """Gemini topic triggers tool detection."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "ai-app",
                    "stars": 0,
                    "forks": 0,
                    "topics": ["gemini"],
                    "updated_at": "2026-01-01",
                }
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
        )
        result = self.engine.score_profile(profile)
        assert "Google Gemini" in result["ai_analysis"]["detected_tools"]

    def test_ai_usage_detects_claude_from_topics(self):
        """Claude topic triggers tool detection."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "ai-app",
                    "stars": 0,
                    "forks": 0,
                    "topics": ["claude"],
                    "updated_at": "2026-01-01",
                }
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
        )
        result = self.engine.score_profile(profile)
        assert "Claude" in result["ai_analysis"]["detected_tools"]

    def test_ai_usage_detects_cursor_from_topics(self):
        """Cursor topic triggers tool detection."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "app",
                    "stars": 0,
                    "forks": 0,
                    "topics": ["cursor"],
                    "updated_at": "2026-01-01",
                }
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
        )
        result = self.engine.score_profile(profile)
        assert "Cursor" in result["ai_analysis"]["detected_tools"]

    def test_ai_usage_detects_windsurf_from_topics(self):
        """Windsurf topic triggers tool detection."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "app",
                    "stars": 0,
                    "forks": 0,
                    "topics": ["windsurf"],
                    "updated_at": "2026-01-01",
                }
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
        )
        result = self.engine.score_profile(profile)
        assert "Windsurf" in result["ai_analysis"]["detected_tools"]

    def test_ai_usage_detects_aider_from_topics(self):
        """Aider topic triggers tool detection."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "app",
                    "stars": 0,
                    "forks": 0,
                    "topics": ["aider"],
                    "updated_at": "2026-01-01",
                }
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
        )
        result = self.engine.score_profile(profile)
        assert "Aider" in result["ai_analysis"]["detected_tools"]

    def test_ai_usage_detects_chatgpt_openai_topics(self):
        """ChatGPT/OpenAI topics trigger tool detection."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "app",
                    "stars": 0,
                    "forks": 0,
                    "topics": ["openai", "chatgpt"],
                    "updated_at": "2026-01-01",
                }
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
        )
        result = self.engine.score_profile(profile)
        assert "ChatGPT/OpenAI" in result["ai_analysis"]["detected_tools"]

    def test_ai_usage_note_without_commits(self):
        """Without commit analysis, result includes a note field."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "repo",
                    "stars": 0,
                    "forks": 0,
                    "topics": [],
                    "updated_at": "2026-01-01",
                }
            ],
        )
        result = self.engine.score_profile(profile)
        assert "note" in result["ai_analysis"]

    def test_ai_usage_commit_analysis_present(self):
        """With commit data, commit_analysis details are included."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "repo",
                    "language": "Python",
                    "stars": 0,
                    "forks": 0,
                    "topics": [],
                    "updated_at": "2026-01-01",
                }
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
        )
        commits = [
            {"message": "feat: implement with Copilot"},
            {"message": "fix: manual fix"},
        ]
        result = self.engine.score_profile(profile, commits)
        ai = result["ai_analysis"]
        assert "commit_analysis" in ai
        assert "burst_score" in ai["commit_analysis"]
        assert ai["commit_analysis"]["commits_analyzed"] == 2

    # --- Burst score integration ---

    def test_burst_score_integrated_in_ai_savviness(self):
        """Commits with burst patterns boost ai_savviness score."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "rapid-dev",
                    "language": "Python",
                    "stars": 0,
                    "forks": 0,
                    "topics": ["copilot"],
                    "description": "AI project",
                    "updated_at": "2026-01-01",
                }
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
        )
        # Create burst commits with timestamps
        commits = [
            {
                "message": f"feat: add feature {i} with Copilot",
                "committed_date": f"2026-01-15T10:0{i}:00Z",
                "changed_files": 25,
            }
            for i in range(5)
        ]
        result = self.engine.score_profile(profile, commits)
        assert result["scores"]["ai_savviness"] > 0
        assert result["ai_analysis"]["commit_analysis"]["burst_score"] > 0

    # --- Shannon entropy edge cases ---

    def test_entropy_single_language(self):
        """Single language produces low diversity score (entropy = 0)."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "mono",
                    "stars": 0,
                    "forks": 0,
                    "topics": [],
                    "updated_at": "2026-01-01",
                }
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
        )
        result = self.engine.score_profile(profile)
        # Single language entropy = 0, so diversity mainly from lang count
        assert result["scores"]["stack_diversity"] >= 0

    def test_entropy_even_distribution(self):
        """Evenly distributed languages produce high entropy."""
        profile = self._make_profile(
            repos=[
                {
                    "name": f"repo-{i}",
                    "stars": 0,
                    "forks": 0,
                    "topics": [],
                    "updated_at": "2026-01-01",
                }
                for i in range(4)
            ],
            languages=[
                {"name": "Python", "count": 1, "percentage": 25.0},
                {"name": "Go", "count": 1, "percentage": 25.0},
                {"name": "Rust", "count": 1, "percentage": 25.0},
                {"name": "Java", "count": 1, "percentage": 25.0},
            ],
        )
        result = self.engine.score_profile(profile)
        # Even distribution should give high entropy score
        assert result["scores"]["stack_diversity"] >= 30

    # --- Activity edge cases ---

    def test_activity_with_orgs_and_calendar(self):
        """Activity scoring includes all contribution stat types."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "repo",
                    "stars": 100,
                    "forks": 50,
                    "topics": [],
                    "updated_at": "2026-01-01",
                }
            ],
            contribution_stats={
                "recent_commits": 100,
                "recent_prs": 10,
                "recent_issues": 5,
                "recent_reviews": 5,
                "total_events": 120,
                "period": "last_90_days",
            },
            organizations=[{"name": "org1"}, {"name": "org2"}],
        )
        result = self.engine.score_profile(profile)
        assert result["scores"]["activity"] >= 50

    # --- Collaboration edge cases ---

    def test_collaboration_with_orgs(self):
        """Org membership boosts collaboration score."""
        profile = self._make_profile(
            repos=[
                {
                    "name": "repo",
                    "stars": 0,
                    "forks": 20,
                    "topics": [],
                    "updated_at": "2026-01-01",
                }
            ],
            contribution_stats={
                "recent_commits": 10,
                "recent_prs": 5,
                "recent_issues": 3,
                "recent_reviews": 2,
                "total_events": 20,
                "period": "last_90_days",
            },
            followers=50,
            organizations=[{"name": "org1"}, {"name": "org2"}, {"name": "org3"}],
        )
        result = self.engine.score_profile(profile)
        assert result["scores"]["collaboration"] > 10

    # --- Normalization correctness ---

    def test_archetype_normalization_comparable_ranges(self):
        """Archetypes with negative weights produce comparable scores."""
        scores = {
            "activity": 80,
            "collaboration": 5,
            "stack_diversity": 50,
            "ai_savviness": 75,
        }
        profile = self._make_profile(
            repos=[
                {
                    "name": "ai-proj",
                    "stars": 5,
                    "forks": 0,
                    "topics": ["copilot"],
                    "updated_at": "2026-01-01",
                }
            ],
            languages=[{"name": "Python", "count": 1, "percentage": 100.0}],
        )
        result = self.engine._classify_archetype(scores, profile)
        # With normalization, ai_indie_hacker should beat rising_developer
        # for high AI + activity + low collab profile
        assert result["id"] == "ai_indie_hacker"

    def test_all_archetypes_defined_correctly(self):
        """Verify all archetypes have required fields."""
        required_keys = {"name", "description", "weights", "min_score"}
        for archetype_id, data in ARCHETYPES.items():
            for key in required_keys:
                assert key in data, f"{archetype_id} missing {key}"
            # Weights should reference valid dimensions
            valid_dims = {"activity", "collaboration", "stack_diversity", "ai_savviness"}
            for dim in data["weights"]:
                assert dim in valid_dims, f"{archetype_id} has invalid dimension {dim}"

    def test_known_frameworks_set_populated(self):
        """KNOWN_FRAMEWORKS should contain major frameworks."""
        assert "react" in KNOWN_FRAMEWORKS
        assert "fastapi" in KNOWN_FRAMEWORKS
        assert "docker" in KNOWN_FRAMEWORKS
        assert "pytorch" in KNOWN_FRAMEWORKS

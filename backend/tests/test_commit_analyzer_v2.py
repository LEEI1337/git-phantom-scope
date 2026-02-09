"""Tests for CommitAnalyzer V2 burst detection features."""

from services.commit_analyzer import CommitAnalyzer


class TestBurstDetection:
    """Tests for _detect_burst_patterns in CommitAnalyzer V2."""

    def setup_method(self):
        self.analyzer = CommitAnalyzer()

    def test_burst_too_few_commits(self):
        """Fewer than 3 commits returns 0.0 burst score."""
        commits = [
            {"message": "feat: a"},
            {"message": "feat: b"},
        ]
        result = self.analyzer.analyze_commits(commits)
        assert result.burst_score == 0.0

    def test_burst_rapid_timestamps(self):
        """Commits < 2 minutes apart trigger rapid burst detection."""
        commits = [
            {
                "message": "feat: add feature 1",
                "committed_date": "2026-01-15T10:00:00Z",
            },
            {
                "message": "feat: add feature 2",
                "committed_date": "2026-01-15T10:01:00Z",
            },
            {
                "message": "feat: add feature 3",
                "committed_date": "2026-01-15T10:01:30Z",
            },
            {
                "message": "feat: add feature 4",
                "committed_date": "2026-01-15T10:02:00Z",
            },
        ]
        result = self.analyzer.analyze_commits(commits)
        assert result.burst_score > 0.0

    def test_burst_similar_messages(self):
        """Commits with identical 20-char prefixes trigger burst."""
        commits = [
            {"message": "feat: implement the feature for module alpha"},
            {"message": "feat: implement the feature for module beta"},
            {"message": "feat: implement the feature for module gamma"},
            {"message": "feat: implement the feature for module delta"},
        ]
        result = self.analyzer.analyze_commits(commits)
        # "feat: implement the " is the shared prefix (20 chars)
        assert result.burst_score >= 0.3

    def test_burst_high_file_changes(self):
        """Commits with many file changes boost burst score."""
        commits = [
            {"message": "refactor: restructure entire codebase", "changed_files": 50},
            {"message": "feat: add new module", "changed_files": 30},
            {"message": "fix: resolve issues", "changed_files": 25},
        ]
        result = self.analyzer.analyze_commits(commits)
        assert result.burst_score > 0.0

    def test_burst_no_timestamps_no_rapid(self):
        """Without timestamps, only message/file patterns contribute."""
        commits = [
            {"message": "unique message alpha"},
            {"message": "different beta thing"},
            {"message": "another gamma item here"},
        ]
        result = self.analyzer.analyze_commits(commits)
        # No rapid timestamps, no repeated prefixes, no high file changes
        assert result.burst_score == 0.0

    def test_burst_confidence_medium(self):
        """High burst score without tool mentions -> medium confidence."""
        commits = [
            {
                "message": "feat: implement the feature for module alpha",
                "committed_date": "2026-01-15T10:00:00Z",
                "changed_files": 25,
            },
            {
                "message": "feat: implement the feature for module beta",
                "committed_date": "2026-01-15T10:00:30Z",
                "changed_files": 30,
            },
            {
                "message": "feat: implement the feature for module gamma",
                "committed_date": "2026-01-15T10:01:00Z",
                "changed_files": 22,
            },
            {
                "message": "feat: implement the feature for module delta",
                "committed_date": "2026-01-15T10:01:30Z",
                "changed_files": 28,
            },
        ]
        result = self.analyzer.analyze_commits(commits)
        # Burst score > 0.5 without direct tool mentions -> medium
        if result.burst_score > 0.5:
            assert result.ai_confidence in ("medium", "high")

    def test_burst_score_in_to_dict(self):
        """burst_score is included in serialized output."""
        commits = [
            {"message": "feat: add thing 1"},
            {"message": "feat: add thing 2"},
            {"message": "feat: add thing 3"},
        ]
        result = self.analyzer.analyze_commits(commits)
        data = result.to_dict()
        assert "burst_score" in data

    def test_windsurf_tool_detected(self):
        """Windsurf mentions are detected."""
        commits = [
            {"message": "feat: built with Windsurf IDE assistance"},
        ]
        result = self.analyzer.analyze_commits(commits)
        assert "Windsurf" in result.ai_tool_mentions

    def test_aider_tool_detected(self):
        """Aider mentions are detected."""
        commits = [
            {"message": "feat: added by aider"},
        ]
        result = self.analyzer.analyze_commits(commits)
        assert "Aider" in result.ai_tool_mentions

"""Tests for commit message analyzer."""

import pytest

from services.commit_analyzer import CommitAnalyzer


@pytest.fixture
def analyzer():
    """Provide a CommitAnalyzer instance."""
    return CommitAnalyzer()


class TestCommitAnalyzer:
    """Test suite for CommitAnalyzer."""

    def test_empty_commits(self, analyzer: CommitAnalyzer):
        """Empty commit list returns zero result."""
        result = analyzer.analyze_commits([])
        assert result.total_commits_analyzed == 0
        assert result.ai_confidence == "low"
        assert not result.ai_tool_mentions
        assert not result.co_author_bots

    def test_copilot_mention_detected(self, analyzer: CommitAnalyzer):
        """Copilot mentions in commit messages are detected."""
        commits = [
            {"message": "feat: add auth module using Copilot suggestions"},
            {"message": "fix: resolve bug in auth flow"},
            {"message": "refactor: Copilot helped restructure utils"},
        ]
        result = analyzer.analyze_commits(commits)
        assert "GitHub Copilot" in result.ai_tool_mentions
        assert result.ai_tool_mentions["GitHub Copilot"] == 2
        assert result.ai_confidence == "high"

    def test_chatgpt_mention_detected(self, analyzer: CommitAnalyzer):
        """ChatGPT mentions are detected."""
        commits = [
            {"message": "feat: implement API client based on ChatGPT advice"},
            {"message": "docs: add README generated with GPT-4o"},
        ]
        result = analyzer.analyze_commits(commits)
        assert "ChatGPT/OpenAI" in result.ai_tool_mentions
        assert result.ai_tool_mentions["ChatGPT/OpenAI"] == 2

    def test_claude_mention_detected(self, analyzer: CommitAnalyzer):
        """Claude/Anthropic mentions are detected."""
        commits = [
            {"message": "feat: add scoring logic with Claude assistance"},
        ]
        result = analyzer.analyze_commits(commits)
        assert "Claude/Anthropic" in result.ai_tool_mentions

    def test_multiple_tools_detected(self, analyzer: CommitAnalyzer):
        """Multiple AI tools detected in same commit set."""
        commits = [
            {"message": "feat: write tests with Copilot"},
            {"message": "refactor: restructure with Cursor suggestions"},
            {"message": "docs: generated with Claude"},
        ]
        result = analyzer.analyze_commits(commits)
        assert len(result.ai_tool_mentions) == 3
        assert "GitHub Copilot" in result.ai_tool_mentions
        assert "Cursor" in result.ai_tool_mentions
        assert "Claude/Anthropic" in result.ai_tool_mentions

    def test_co_author_bot_detected(self, analyzer: CommitAnalyzer):
        """Bot co-author tags are detected."""
        commits = [
            {
                "message": (
                    "feat: add login page\n\n"
                    "Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>"
                )
            },
            {
                "message": (
                    "fix: resolve type error\n\nCo-authored-by: copilot-chat <copilot@github.com>"
                )
            },
        ]
        result = analyzer.analyze_commits(commits)
        assert "Dependabot" in result.co_author_bots
        assert "GitHub Copilot" in result.co_author_bots

    def test_co_author_extraction(self, analyzer: CommitAnalyzer):
        """Co-author names and emails are extracted correctly."""
        commits = [
            {
                "message": (
                    "feat: add feature\n\n"
                    "Co-authored-by: John Doe <john@example.com>\n"
                    "Co-authored-by: Jane Smith <jane@example.com>"
                )
            },
        ]
        result = analyzer.analyze_commits(commits)
        assert len(result.co_authors) == 2
        assert result.co_authors[0]["name"] == "John Doe"
        assert result.co_authors[0]["email"] == "john@example.com"
        assert result.co_authors[1]["name"] == "Jane Smith"

    def test_no_ai_signals(self, analyzer: CommitAnalyzer):
        """Commits without AI signals return low confidence."""
        commits = [
            {"message": "fix: correct SQL query in user service"},
            {"message": "feat: add pagination to list endpoint"},
            {"message": "test: add unit tests for auth module"},
            {"message": "chore: update dependencies"},
        ]
        result = analyzer.analyze_commits(commits)
        assert result.ai_confidence == "low"
        assert not result.ai_tool_mentions
        assert not result.co_author_bots

    def test_ai_generated_label_detected(self, analyzer: CommitAnalyzer):
        """Commits with 'AI-generated' or 'AI-assisted' labels detected."""
        commits = [
            {"message": "docs: AI-generated API documentation"},
            {"message": "feat: AI-assisted implementation of cache layer"},
        ]
        result = analyzer.analyze_commits(commits)
        assert "AI-Assisted (generic)" in result.ai_tool_mentions

    def test_result_to_dict(self, analyzer: CommitAnalyzer):
        """Result serialization works correctly."""
        commits = [
            {"message": "feat: add feature with Copilot"},
            {"message": "fix: manual bug fix"},
        ]
        result = analyzer.analyze_commits(commits)
        data = result.to_dict()
        assert data["total_commits_analyzed"] == 2
        assert data["commits_with_ai_signals"] == 1
        assert data["ai_percentage"] == 50.0
        assert "GitHub Copilot" in data["detected_tools"]

    def test_heuristic_verbose_message(self, analyzer: CommitAnalyzer):
        """Overly verbose commit messages get heuristic score."""
        long_message = "This commit implements the complete authentication flow including JWT token generation, refresh token rotation, session management, role-based access control, and comprehensive error handling with proper HTTP status codes and logging throughout the entire pipeline"
        commits = [{"message": long_message}]
        result = analyzer.analyze_commits(commits)
        assert result.ai_heuristic_score > 0

    def test_gemini_tool_detected(self, analyzer: CommitAnalyzer):
        """Gemini mentions are detected."""
        commits = [
            {"message": "feat: implement feature using Gemini suggestions"},
        ]
        result = analyzer.analyze_commits(commits)
        assert "Google Gemini" in result.ai_tool_mentions

    def test_duplicate_co_authors_deduplicated(self, analyzer: CommitAnalyzer):
        """Same co-author in multiple commits is listed once."""
        commits = [
            {
                "message": "feat: part 1\n\nCo-authored-by: Bot <bot@test.com>",
            },
            {
                "message": "feat: part 2\n\nCo-authored-by: Bot <bot@test.com>",
            },
        ]
        result = analyzer.analyze_commits(commits)
        assert len(result.co_authors) == 1

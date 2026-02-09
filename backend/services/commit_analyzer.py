"""Commit Message Analyzer for AI Detection.

Analyzes commit messages, co-author tags, and commit patterns
to detect AI-assisted code contributions.

Detects:
- AI tool mentions (Copilot, ChatGPT, Cursor, etc.)
- Co-authored-by bot tags (GitHub Copilot, dependabot, etc.)
- AI-generated commit patterns (generic messages, bulk changes)
- Automated tool signatures

PRIVACY: Analysis is done in-memory only. No commit data persisted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.logging_config import get_logger

logger = get_logger(__name__)


# --- AI Detection Patterns ---

# Direct mentions of AI tools in commit messages
AI_TOOL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bcopilot\b", re.IGNORECASE), "GitHub Copilot"),
    (
        re.compile(r"\bchatgpt\b|\bchat-gpt\b|\bgpt-4o?\b|\bgpt-3\.?5\b", re.IGNORECASE),
        "ChatGPT/OpenAI",
    ),
    (re.compile(r"\bgemini\b", re.IGNORECASE), "Google Gemini"),
    (re.compile(r"\bclaude\b|\banthrop", re.IGNORECASE), "Claude/Anthropic"),
    (re.compile(r"\bcursor\b", re.IGNORECASE), "Cursor"),
    (re.compile(r"\bcodeium\b", re.IGNORECASE), "Codeium"),
    (re.compile(r"\btabnine\b", re.IGNORECASE), "Tabnine"),
    (re.compile(r"\bcody\b", re.IGNORECASE), "Sourcegraph Cody"),
    (re.compile(r"\bsupermaven\b", re.IGNORECASE), "Supermaven"),
    (
        re.compile(r"\bai[- ]generated\b|\bai[- ]assisted\b|\bai[- ]powered\b", re.IGNORECASE),
        "AI-Assisted (generic)",
    ),
    (
        re.compile(r"\bgenerated\s+(?:by|with|using)\s+ai\b", re.IGNORECASE),
        "AI-Generated (generic)",
    ),
    (re.compile(r"\bllm\b|\blarge\s+language\s+model\b", re.IGNORECASE), "LLM (generic)"),
]

# Co-authored-by patterns indicating bot/AI contributions
CO_AUTHOR_BOT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"co-authored-by:\s*.*copilot", re.IGNORECASE), "GitHub Copilot"),
    (re.compile(r"co-authored-by:\s*.*\[bot\]", re.IGNORECASE), "Bot"),
    (re.compile(r"co-authored-by:\s*.*dependabot", re.IGNORECASE), "Dependabot"),
    (re.compile(r"co-authored-by:\s*.*renovate", re.IGNORECASE), "Renovate"),
    (re.compile(r"co-authored-by:\s*.*snyk", re.IGNORECASE), "Snyk"),
    (re.compile(r"co-authored-by:\s*.*github-actions", re.IGNORECASE), "GitHub Actions"),
    (re.compile(r"co-authored-by:\s*.*deepsource", re.IGNORECASE), "DeepSource"),
]

# Patterns suggesting AI-generated commit messages (heuristic)
AI_MESSAGE_HEURISTICS: list[tuple[re.Pattern[str], str, float]] = [
    # Very generic, potentially auto-generated messages
    (
        re.compile(r"^(update|fix|refactor|improve|add|remove|clean)\s+\w+$", re.IGNORECASE),
        "generic_single_word_action",
        0.1,
    ),
    # Overly detailed single-line commits (AI tends to be verbose)
    (re.compile(r"^.{150,}$"), "overly_verbose_single_line", 0.15),
    # Conventional commit with very detailed scope
    (
        re.compile(r"^(feat|fix|docs|style|refactor|test|chore)\(.{30,}\):", re.IGNORECASE),
        "detailed_conventional_commit",
        0.05,
    ),
    # "Implement" or "Implemented" as first word (common AI pattern)
    (re.compile(r"^implement(ed|s|ing)?\s", re.IGNORECASE), "implement_prefix", 0.1),
    # Long descriptive messages starting with articles
    (
        re.compile(
            r"^(This|The|A|An)\s+(commit|change|update|patch|PR|pull request)\s", re.IGNORECASE
        ),
        "article_prefix_commit",
        0.2,
    ),
]

# Co-author extraction regex
CO_AUTHOR_REGEX = re.compile(
    r"co-authored-by:\s*(.+?)\s*<(.+?)>",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class CommitAnalysisResult:
    """Result of analyzing commits for AI usage."""

    total_commits_analyzed: int = 0
    ai_tool_mentions: dict[str, int] = field(default_factory=dict)
    co_author_bots: dict[str, int] = field(default_factory=dict)
    co_authors: list[dict[str, str]] = field(default_factory=list)
    ai_heuristic_score: float = 0.0
    ai_confidence: str = "low"
    commits_with_ai_signals: int = 0
    ai_signal_details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "total_commits_analyzed": self.total_commits_analyzed,
            "ai_tool_mentions": self.ai_tool_mentions,
            "co_author_bots": self.co_author_bots,
            "co_authors": self.co_authors,
            "ai_heuristic_score": round(self.ai_heuristic_score, 2),
            "ai_confidence": self.ai_confidence,
            "commits_with_ai_signals": self.commits_with_ai_signals,
            "detected_tools": sorted(self.ai_tool_mentions.keys()),
            "ai_percentage": (
                round(self.commits_with_ai_signals / self.total_commits_analyzed * 100, 1)
                if self.total_commits_analyzed > 0
                else 0.0
            ),
        }


class CommitAnalyzer:
    """Analyzes commit messages for AI tool usage and patterns."""

    def analyze_commits(self, commits: list[dict[str, Any]]) -> CommitAnalysisResult:
        """Analyze a list of commits for AI signals.

        Args:
            commits: List of commit dicts with 'message', 'author_name',
                     'committed_date' etc.

        Returns:
            CommitAnalysisResult with detected AI tools, co-authors, scores
        """
        result = CommitAnalysisResult(total_commits_analyzed=len(commits))

        if not commits:
            return result

        for commit in commits:
            message = commit.get("message", "")
            has_ai_signal = False

            # Check for AI tool mentions
            for pattern, tool_name in AI_TOOL_PATTERNS:
                if pattern.search(message):
                    result.ai_tool_mentions[tool_name] = (
                        result.ai_tool_mentions.get(tool_name, 0) + 1
                    )
                    has_ai_signal = True

            # Check for co-author bots
            for pattern, bot_name in CO_AUTHOR_BOT_PATTERNS:
                if pattern.search(message):
                    result.co_author_bots[bot_name] = result.co_author_bots.get(bot_name, 0) + 1
                    has_ai_signal = True

            # Extract all co-authors
            co_authors = self._extract_co_authors(message)
            for ca in co_authors:
                if ca not in result.co_authors:
                    result.co_authors.append(ca)

            # Apply heuristic scoring
            heuristic_score = self._apply_heuristics(message)
            result.ai_heuristic_score += heuristic_score

            if has_ai_signal:
                result.commits_with_ai_signals += 1

        # Normalize heuristic score (0-100)
        if result.total_commits_analyzed > 0:
            result.ai_heuristic_score = min(
                result.ai_heuristic_score / result.total_commits_analyzed * 100,
                100.0,
            )

        # Determine confidence level
        result.ai_confidence = self._determine_confidence(result)

        return result

    def _extract_co_authors(self, message: str) -> list[dict[str, str]]:
        """Extract co-author tags from commit message."""
        matches = CO_AUTHOR_REGEX.findall(message)
        return [{"name": name.strip(), "email": email.strip()} for name, email in matches]

    def _apply_heuristics(self, message: str) -> float:
        """Apply heuristic patterns to estimate AI-generation likelihood."""
        score = 0.0
        for pattern, _name, weight in AI_MESSAGE_HEURISTICS:
            if pattern.search(message):
                score += weight
        return min(score, 1.0)

    def _determine_confidence(self, result: CommitAnalysisResult) -> str:
        """Determine confidence level of AI detection.

        high: Direct tool mentions or bot co-authors found
        medium: Heuristic patterns suggest AI usage
        low: No significant AI signals
        """
        if result.ai_tool_mentions or result.co_author_bots:
            return "high"

        if result.total_commits_analyzed > 0:
            ai_ratio = result.commits_with_ai_signals / result.total_commits_analyzed
            if ai_ratio > 0.3:
                return "medium"
            if result.ai_heuristic_score > 30:
                return "medium"

        return "low"

"""Analytics & Scoring Engine.

Scores GitHub profiles across 4 dimensions and assigns developer archetypes.
Includes AI code detection via commit message analysis and heuristics.

PRIVACY: Scoring is done in-memory. Only anonymous bucket data
is persisted to PostgreSQL for trend analytics.
"""

from __future__ import annotations

import re
from typing import Any

from app.logging_config import get_logger
from app.metrics import ARCHETYPES_ASSIGNED, SCORING_DURATION
from services.commit_analyzer import CommitAnalysisResult, CommitAnalyzer

logger = get_logger(__name__)

# AI-related patterns in commit messages
AI_COMMIT_PATTERNS = [
    re.compile(r"copilot", re.IGNORECASE),
    re.compile(r"chatgpt|chat-gpt|gpt-4|gpt-3", re.IGNORECASE),
    re.compile(r"gemini|bard", re.IGNORECASE),
    re.compile(r"claude|anthropic", re.IGNORECASE),
    re.compile(r"ai[- ]generated", re.IGNORECASE),
    re.compile(r"ai[- ]assisted", re.IGNORECASE),
    re.compile(r"cursor|codeium|tabnine|cody", re.IGNORECASE),
    re.compile(r"co-authored-by:.*\[bot\]", re.IGNORECASE),
    re.compile(r"co-authored-by:.*copilot", re.IGNORECASE),
]

# Developer archetype definitions
ARCHETYPES = {
    "ai_indie_hacker": {
        "name": "AI-Driven Indie Hacker",
        "description": "High AI usage, high activity, low collaboration",
        "conditions": lambda s: s["ai_savviness"] >= 70 and s["activity"] >= 60 and s["collaboration"] < 40,
    },
    "open_source_maintainer": {
        "name": "Open Source Maintainer",
        "description": "High collaboration, high activity, community-focused",
        "conditions": lambda s: s["collaboration"] >= 70 and s["activity"] >= 60,
    },
    "full_stack_polyglot": {
        "name": "Full-Stack Polyglot",
        "description": "High stack diversity, well-rounded skills",
        "conditions": lambda s: s["stack_diversity"] >= 70 and s["activity"] >= 40,
    },
    "devops_specialist": {
        "name": "DevOps & Infrastructure Expert",
        "description": "Infrastructure-focused with CI/CD and cloud expertise",
        "conditions": lambda s: s["stack_diversity"] >= 50 and s["activity"] >= 50,
    },
    "data_scientist": {
        "name": "Data Science Specialist",
        "description": "Python/R focused with ML/AI framework usage",
        "conditions": lambda s: s["ai_savviness"] >= 50 and s["stack_diversity"] >= 40,
    },
    "rising_developer": {
        "name": "Rising Developer",
        "description": "Growing activity, learning phase",
        "conditions": lambda s: s["activity"] >= 30,
    },
    "code_explorer": {
        "name": "Code Explorer",
        "description": "Diverse interests, experimental approach",
        "conditions": lambda s: True,  # Fallback
    },
}


class ScoringEngine:
    """Profile scoring and archetype classification engine."""

    def __init__(self) -> None:
        self.commit_analyzer = CommitAnalyzer()

    @SCORING_DURATION.time()
    def score_profile(
        self,
        profile: dict[str, Any],
        commit_data: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Score a GitHub profile across all dimensions.

        Args:
            profile: GitHub profile data from GitHubService
            commit_data: Optional list of commits for deeper AI analysis

        Returns:
            Scoring result with scores, archetype, and AI analysis
        """
        # Analyze commits if available
        commit_analysis: CommitAnalysisResult | None = None
        if commit_data:
            commit_analysis = self.commit_analyzer.analyze_commits(commit_data)

        activity = self._score_activity(profile)
        collaboration = self._score_collaboration(profile)
        stack_diversity = self._score_stack_diversity(profile)
        ai_savviness = self._score_ai_savviness(profile, commit_analysis)

        scores = {
            "activity": activity,
            "collaboration": collaboration,
            "stack_diversity": stack_diversity,
            "ai_savviness": ai_savviness,
        }

        archetype = self._classify_archetype(scores, profile)
        ai_analysis = self._analyze_ai_usage(profile, commit_analysis)

        ARCHETYPES_ASSIGNED.labels(archetype=archetype["id"]).inc()

        return {
            "scores": scores,
            "archetype": archetype,
            "ai_analysis": ai_analysis,
            "tech_profile": self._build_tech_profile(profile),
        }

    def _score_activity(self, profile: dict[str, Any]) -> int:
        """Score developer activity (0-100).

        Factors: repo count, recent commits, update frequency, account age.
        """
        score = 0.0
        repos = profile.get("repos", [])
        stats = profile.get("contribution_stats", {})

        # Repo count (max 30 points)
        repo_count = len(repos)
        score += min(repo_count / 50 * 30, 30)

        # Recent commits (max 30 points)
        recent_commits = stats.get("recent_commits", 0)
        score += min(recent_commits / 100 * 30, 30)

        # Active repos (updated in last 6 months) (max 20 points)
        active_repos = sum(1 for r in repos if r.get("updated_at", "")[:4] >= "2025")
        score += min(active_repos / 10 * 20, 20)

        # Stars received (max 20 points)
        total_stars = sum(r.get("stars", 0) for r in repos)
        score += min(total_stars / 100 * 20, 20)

        return min(int(score), 100)

    def _score_collaboration(self, profile: dict[str, Any]) -> int:
        """Score collaboration level (0-100).

        Factors: PRs, issues, reviews, followers ratio, forks received.
        """
        score = 0.0
        stats = profile.get("contribution_stats", {})
        repos = profile.get("repos", [])

        # Recent PRs (max 25 points)
        score += min(stats.get("recent_prs", 0) / 10 * 25, 25)

        # Recent issues (max 15 points)
        score += min(stats.get("recent_issues", 0) / 10 * 15, 15)

        # Reviews (max 20 points)
        score += min(stats.get("recent_reviews", 0) / 5 * 20, 20)

        # Followers (max 20 points)
        followers = profile.get("followers", 0)
        score += min(followers / 50 * 20, 20)

        # Forks received (max 20 points)
        total_forks = sum(r.get("forks", 0) for r in repos)
        score += min(total_forks / 50 * 20, 20)

        return min(int(score), 100)

    def _score_stack_diversity(self, profile: dict[str, Any]) -> int:
        """Score stack/language diversity (0-100).

        Factors: number of languages, framework breadth, topic variety.
        """
        score = 0.0
        languages = profile.get("languages", [])
        repos = profile.get("repos", [])

        # Number of languages (max 40 points)
        lang_count = len(languages)
        score += min(lang_count / 8 * 40, 40)

        # Language distribution (max 30 points) - penalize single-language dominance
        if languages:
            if isinstance(languages, dict):
                top_lang_pct = max(languages.values()) if languages else 100
            else:
                top_lang_pct = languages[0].get("percentage", 100)
            diversity_factor = 1 - (top_lang_pct / 100)
            score += diversity_factor * 30

        # Topic variety (max 30 points)
        all_topics: set[str] = set()
        for repo in repos:
            all_topics.update(repo.get("topics", []))
        score += min(len(all_topics) / 15 * 30, 30)

        return min(int(score), 100)

    def _score_ai_savviness(
        self,
        profile: dict[str, Any],
        commit_analysis: CommitAnalysisResult | None = None,
    ) -> int:
        """Score AI-savviness (0-100).

        Factors:
        - AI tool mentions in repos (topics, names, descriptions)
        - ML/AI framework usage (language indicators)
        - Commit message AI signals (direct mentions, co-author bots)
        - Heuristic patterns in commit messages
        """
        score = 0.0
        repos = profile.get("repos", [])

        # AI-related topics (max 20 points)
        ai_topics = {
            "machine-learning", "deep-learning", "artificial-intelligence",
            "ai", "ml", "nlp", "llm", "gpt", "transformers",
            "neural-network", "computer-vision", "data-science",
            "chatgpt", "copilot", "generative-ai",
        }
        all_topics: set[str] = set()
        for repo in repos:
            all_topics.update(t.lower() for t in repo.get("topics", []))

        ai_topic_count = len(all_topics & ai_topics)
        score += min(ai_topic_count / 5 * 20, 20)

        # AI framework languages (max 15 points)
        ai_languages = {"Python", "Jupyter Notebook", "R"}
        languages = profile.get("languages", [])
        if isinstance(languages, dict):
            lang_names = set(languages.keys())
        else:
            lang_names = {lang["name"] for lang in languages}
        ai_lang_count = len(lang_names & ai_languages)
        score += min(ai_lang_count / 2 * 15, 15)

        # AI repo names/descriptions (max 15 points)
        ai_name_patterns = re.compile(
            r"ai|ml|gpt|llm|neural|model|predict|classify|detect|nlp|bert|transformer",
            re.IGNORECASE,
        )
        ai_repos = sum(
            1
            for r in repos
            if ai_name_patterns.search(r.get("name", ""))
            or ai_name_patterns.search(r.get("description", "") or "")
        )
        score += min(ai_repos / 5 * 15, 15)

        # Commit analysis signals (max 35 points - biggest factor)
        if commit_analysis and commit_analysis.total_commits_analyzed > 0:
            # Direct AI tool mentions in commits (max 20 points)
            total_mentions = sum(commit_analysis.ai_tool_mentions.values())
            mention_ratio = total_mentions / commit_analysis.total_commits_analyzed
            score += min(mention_ratio * 100, 20)

            # Co-author bot tags (max 10 points)
            total_bots = sum(commit_analysis.co_author_bots.values())
            bot_ratio = total_bots / commit_analysis.total_commits_analyzed
            score += min(bot_ratio * 50, 10)

            # Heuristic score contribution (max 5 points)
            score += min(commit_analysis.ai_heuristic_score / 20, 5)

        # Bonus for high repo count with AI focus (max 15 points)
        if len(repos) > 0:
            ai_repo_ratio = ai_repos / len(repos)
            score += ai_repo_ratio * 15

        return min(int(score), 100)

    def _classify_archetype(
        self, scores: dict[str, int], profile: dict[str, Any]
    ) -> dict[str, str]:
        """Classify developer archetype based on scores."""
        for archetype_id, archetype in ARCHETYPES.items():
            if archetype["conditions"](scores):
                return {
                    "id": archetype_id,
                    "name": archetype["name"],
                    "description": archetype["description"],
                }

        # Fallback (should never reach here due to code_explorer)
        return {
            "id": "code_explorer",
            "name": "Code Explorer",
            "description": "Diverse interests, experimental approach",
        }

    def _analyze_ai_usage(
        self,
        profile: dict[str, Any],
        commit_analysis: CommitAnalysisResult | None = None,
    ) -> dict[str, Any]:
        """Analyze AI tool usage based on available data.

        Combines repo metadata heuristics with commit message analysis
        for comprehensive AI usage detection.
        """
        repos = profile.get("repos", [])

        # Determine AI score bucket
        ai_score = self._score_ai_savviness(profile, commit_analysis)
        if ai_score >= 60:
            bucket = "60_100"
        elif ai_score >= 30:
            bucket = "30_60"
        elif ai_score >= 10:
            bucket = "10_30"
        else:
            bucket = "0_10"

        # Detect AI tools from repo topics and names
        detected_tools: set[str] = set()
        for repo in repos:
            topics = repo.get("topics", [])
            for topic in topics:
                topic_lower = topic.lower()
                if "copilot" in topic_lower:
                    detected_tools.add("GitHub Copilot")
                if "chatgpt" in topic_lower or "openai" in topic_lower:
                    detected_tools.add("ChatGPT/OpenAI")
                if "gemini" in topic_lower or "bard" in topic_lower:
                    detected_tools.add("Google Gemini")
                if "claude" in topic_lower:
                    detected_tools.add("Claude")
                if "cursor" in topic_lower:
                    detected_tools.add("Cursor")

        # Merge tools from commit analysis
        confidence = "estimated"
        commit_details: dict[str, Any] = {}
        if commit_analysis:
            detected_tools.update(commit_analysis.ai_tool_mentions.keys())
            confidence = commit_analysis.ai_confidence
            commit_details = {
                "commits_analyzed": commit_analysis.total_commits_analyzed,
                "ai_signals_found": commit_analysis.commits_with_ai_signals,
                "ai_percentage": (
                    round(
                        commit_analysis.commits_with_ai_signals
                        / commit_analysis.total_commits_analyzed
                        * 100,
                        1,
                    )
                    if commit_analysis.total_commits_analyzed > 0
                    else 0.0
                ),
                "co_author_bots": commit_analysis.co_author_bots,
                "co_authors": commit_analysis.co_authors[:10],
            }

        result: dict[str, Any] = {
            "overall_bucket": bucket,
            "detected_tools": sorted(detected_tools),
            "confidence": confidence,
        }

        if commit_details:
            result["commit_analysis"] = commit_details
        else:
            result["note"] = (
                "Based on public repository metadata. "
                "Commit analysis available with GitHub token."
            )

        return result

    def _build_tech_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        """Build a summarized tech profile for prompt orchestration."""
        repos = profile.get("repos", [])
        languages = profile.get("languages", [])

        # Detect frameworks from repo topics
        framework_topics = set()
        for repo in repos:
            framework_topics.update(repo.get("topics", []))

        known_frameworks = {
            "react", "nextjs", "vue", "angular", "svelte",
            "fastapi", "django", "flask", "express", "nestjs",
            "pytorch", "tensorflow", "langchain", "docker", "kubernetes",
            "tailwindcss", "graphql", "postgres", "mongodb",
        }
        detected_frameworks = sorted(framework_topics & known_frameworks)

        # Top repos by stars
        top_repos = sorted(repos, key=lambda r: r.get("stars", 0), reverse=True)[:5]

        return {
            "languages": list(languages.keys())[:10] if isinstance(languages, dict) else languages[:10],
            "frameworks": detected_frameworks[:15],
            "top_repos": [
                {
                    "name": r["name"],
                    "language": r.get("language"),
                    "stars": r.get("stars", 0),
                    "description": (r.get("description") or "")[:100],
                }
                for r in top_repos
            ],
        }

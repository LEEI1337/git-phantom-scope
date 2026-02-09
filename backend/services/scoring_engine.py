"""Analytics & Scoring Engine V2.

Scores GitHub profiles across 4 dimensions and assigns developer archetypes.
Includes AI code detection via commit message analysis and heuristics.

V2 Improvements:
- Logarithmic scaling for diminishing returns on high counts
- Time-decay weighting for activity recency
- Framework-level diversity scoring (Shannon entropy)
- Multi-archetype classification with confidence ranking
- Streak bonus and consistency metrics
- AI config file detection

PRIVACY: Scoring is done in-memory. Only anonymous bucket data
is persisted to PostgreSQL for trend analytics.
"""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime
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

# AI config files that indicate AI tool usage
AI_CONFIG_FILES = {
    ".github/copilot-instructions.md",
    ".cursorrules",
    ".cursorignore",
    ".aider",
    ".aider.conf.yml",
    ".codeiumrc",
    ".tabnine",
    ".continue/config.json",
    "CLAUDE.md",
    ".windsurfrules",
}

# Developer archetype definitions with weighted scoring
ARCHETYPES = {
    "ai_indie_hacker": {
        "name": "AI-Driven Indie Hacker",
        "description": "High AI usage, high activity, low collaboration",
        "weights": {
            "ai_savviness": 0.4,
            "activity": 0.35,
            "collaboration": -0.2,
            "stack_diversity": 0.05,
        },
        "min_score": 55,
    },
    "open_source_maintainer": {
        "name": "Open Source Maintainer",
        "description": "High collaboration, high activity, community-focused developer",
        "weights": {
            "collaboration": 0.4,
            "activity": 0.35,
            "stack_diversity": 0.15,
            "ai_savviness": 0.1,
        },
        "min_score": 50,
    },
    "full_stack_polyglot": {
        "name": "Full-Stack Polyglot",
        "description": "High stack diversity, well-rounded skills across many technologies",
        "weights": {
            "stack_diversity": 0.45,
            "activity": 0.25,
            "collaboration": 0.15,
            "ai_savviness": 0.15,
        },
        "min_score": 45,
    },
    "backend_architect": {
        "name": "Backend Architect",
        "description": "Systems-focused with strong backend and infrastructure skills",
        "weights": {
            "activity": 0.3,
            "stack_diversity": 0.25,
            "collaboration": 0.25,
            "ai_savviness": 0.2,
        },
        "min_score": 40,
        "requires": {"backend_langs": True},
    },
    "frontend_craftsman": {
        "name": "Frontend Craftsman",
        "description": "UI/UX focused developer with modern frontend framework expertise",
        "weights": {
            "stack_diversity": 0.3,
            "activity": 0.3,
            "collaboration": 0.2,
            "ai_savviness": 0.2,
        },
        "min_score": 40,
        "requires": {"frontend_langs": True},
    },
    "devops_specialist": {
        "name": "DevOps & Infrastructure Expert",
        "description": "Infrastructure-focused with CI/CD, cloud, and containerization expertise",
        "weights": {
            "stack_diversity": 0.3,
            "activity": 0.3,
            "collaboration": 0.2,
            "ai_savviness": 0.2,
        },
        "min_score": 40,
        "requires": {"devops_topics": True},
    },
    "data_scientist": {
        "name": "Data Science Specialist",
        "description": "Python/R focused with ML/AI framework usage",
        "weights": {
            "ai_savviness": 0.35,
            "stack_diversity": 0.25,
            "activity": 0.25,
            "collaboration": 0.15,
        },
        "min_score": 40,
        "requires": {"data_science_langs": True},
    },
    "security_sentinel": {
        "name": "Security Sentinel",
        "description": "Security-focused developer with vulnerability research or security tooling",
        "weights": {
            "activity": 0.3,
            "stack_diversity": 0.25,
            "collaboration": 0.25,
            "ai_savviness": 0.2,
        },
        "min_score": 35,
        "requires": {"security_topics": True},
    },
    "rising_developer": {
        "name": "Rising Developer",
        "description": "Growing activity, learning phase, building momentum",
        "weights": {
            "activity": 0.4,
            "stack_diversity": 0.25,
            "ai_savviness": 0.2,
            "collaboration": 0.15,
        },
        "min_score": 20,
    },
    "code_explorer": {
        "name": "Code Explorer",
        "description": "Diverse interests, experimental approach, exploring the ecosystem",
        "weights": {
            "stack_diversity": 0.3,
            "activity": 0.3,
            "ai_savviness": 0.2,
            "collaboration": 0.2,
        },
        "min_score": 0,
    },
}

# Language group indicators for archetype requirements
BACKEND_LANGUAGES = {
    "Python",
    "Java",
    "Go",
    "Rust",
    "C#",
    "C++",
    "Ruby",
    "PHP",
    "Kotlin",
    "Scala",
    "Elixir",
}
FRONTEND_LANGUAGES = {
    "TypeScript",
    "JavaScript",
    "CSS",
    "HTML",
    "Svelte",
    "Vue",
    "Dart",
}
DATA_SCIENCE_LANGUAGES = {"Python", "Jupyter Notebook", "R", "Julia"}
DEVOPS_TOPICS = {
    "docker",
    "kubernetes",
    "terraform",
    "ansible",
    "ci-cd",
    "devops",
    "aws",
    "gcp",
    "azure",
    "helm",
    "jenkins",
    "github-actions",
}
SECURITY_TOPICS = {
    "security",
    "vulnerability",
    "pentest",
    "ctf",
    "exploit",
    "cybersecurity",
    "infosec",
    "cryptography",
    "owasp",
}

# Framework detection from repo topics
KNOWN_FRAMEWORKS = {
    "react",
    "nextjs",
    "vue",
    "angular",
    "svelte",
    "fastapi",
    "django",
    "flask",
    "express",
    "nestjs",
    "pytorch",
    "tensorflow",
    "langchain",
    "docker",
    "kubernetes",
    "tailwindcss",
    "graphql",
    "postgres",
    "mongodb",
    "spring",
    "rails",
    "laravel",
    "gin",
    "actix",
    "rocket",
    "deno",
    "bun",
    "remix",
    "nuxt",
    "astro",
    "solidjs",
    "htmx",
    "prisma",
    "drizzle",
    "supabase",
    "firebase",
    "vercel",
    "aws",
    "gcp",
    "azure",
}


def _log_scale(value: float, max_val: float, points: float) -> float:
    """Logarithmic scaling for diminishing returns.

    Maps [0, inf) to [0, points] with fast initial growth
    and diminishing returns past the reference max_val.
    """
    if value <= 0:
        return 0.0
    scaled = math.log1p(value) / math.log1p(max_val) * points
    return min(scaled, points)


def _time_decay_weight(date_str: str | None, half_life_days: int = 180) -> float:
    """Calculate time-decay weight (0.0 to 1.0).

    Recent dates get weight closer to 1.0, older dates decay exponentially.
    Half-life determines how fast the decay is (default 6 months).
    """
    if not date_str:
        return 0.0
    try:
        dt_str = date_str[:19].replace("T", " ")
        if len(dt_str) == 10:
            dt = datetime.strptime(dt_str, "%Y-%m-%d").replace(tzinfo=UTC)
        else:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        days_ago = (datetime.now(UTC) - dt).days
        return math.exp(-0.693 * days_ago / half_life_days)  # 0.693 = ln(2)
    except (ValueError, TypeError):
        return 0.0


class ScoringEngine:
    """Profile scoring and archetype classification engine V2."""

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

        V2: Logarithmic scaling, time-decay weighting, consistency bonus.
        """
        score = 0.0
        repos = profile.get("repos", [])
        stats = profile.get("contribution_stats", {})

        # Repo count - log scale (max 25 points)
        repo_count = len(repos)
        score += _log_scale(repo_count, 50, 25)

        # Recent commits - log scale (max 25 points)
        recent_commits = stats.get("recent_commits", 0)
        score += _log_scale(recent_commits, 100, 25)

        # Repo freshness with time-decay (max 25 points)
        if repos:
            freshness_sum = sum(
                _time_decay_weight(r.get("updated_at"), half_life_days=180) for r in repos
            )
            freshness_score = min(freshness_sum / 5.0, 1.0)
            score += freshness_score * 25

        # Stars received - log scale (max 15 points)
        total_stars = sum(r.get("stars", 0) for r in repos)
        score += _log_scale(total_stars, 200, 15)

        # Consistency bonus: event type diversity (max 10 points)
        event_types = 0
        if stats.get("recent_commits", 0) > 0:
            event_types += 1
        if stats.get("recent_prs", 0) > 0:
            event_types += 1
        if stats.get("recent_issues", 0) > 0:
            event_types += 1
        if stats.get("recent_reviews", 0) > 0:
            event_types += 1
        score += (event_types / 4) * 10

        return min(int(score), 100)

    def _score_collaboration(self, profile: dict[str, Any]) -> int:
        """Score collaboration level (0-100).

        V2: Log scaling, follower ratio, org membership bonus.
        """
        score = 0.0
        stats = profile.get("contribution_stats", {})
        repos = profile.get("repos", [])

        # Recent PRs - log scale (max 20 points)
        score += _log_scale(stats.get("recent_prs", 0), 15, 20)

        # Recent issues - log scale (max 12 points)
        score += _log_scale(stats.get("recent_issues", 0), 10, 12)

        # Reviews given (max 20 points)
        score += _log_scale(stats.get("recent_reviews", 0), 8, 20)

        # Follower score with log scaling (max 18 points)
        followers = profile.get("followers", 0)
        score += _log_scale(followers, 100, 18)

        # Follower/following ratio bonus (max 10 points)
        following = max(profile.get("following", 0), 1)
        ratio = followers / following
        score += min(ratio * 3, 10)

        # Forks received (max 15 points)
        total_forks = sum(r.get("forks", 0) for r in repos)
        score += _log_scale(total_forks, 50, 15)

        # Org membership bonus (max 5 points)
        orgs = profile.get("organizations", [])
        score += min(len(orgs) * 2.5, 5)

        return min(int(score), 100)

    def _score_stack_diversity(self, profile: dict[str, Any]) -> int:
        """Score stack/language diversity (0-100).

        V2: Shannon entropy for distribution, framework detection, ecosystem breadth.
        """
        score = 0.0
        languages = profile.get("languages", [])
        repos = profile.get("repos", [])

        # Number of languages - log scale (max 30 points)
        lang_count = len(languages)
        score += _log_scale(lang_count, 10, 30)

        # Language distribution evenness via Shannon entropy (max 25 points)
        if languages:
            if isinstance(languages, dict):
                total = sum(languages.values()) or 1
                fractions = [v / total for v in languages.values()]
            else:
                fractions = [lang.get("percentage", 0) / 100 for lang in languages]

            entropy = 0.0
            for frac in fractions:
                if frac > 0:
                    entropy -= frac * math.log2(frac)
            max_entropy = math.log2(max(lang_count, 2))
            evenness = entropy / max_entropy if max_entropy > 0 else 0
            score += evenness * 25

        # Framework detection from topics (max 25 points)
        all_topics: set[str] = set()
        for repo in repos:
            all_topics.update(t.lower() for t in repo.get("topics", []))
        detected_frameworks = all_topics & KNOWN_FRAMEWORKS
        score += _log_scale(len(detected_frameworks), 8, 25)

        # Topic variety beyond frameworks (max 20 points)
        non_framework_topics = all_topics - KNOWN_FRAMEWORKS
        score += _log_scale(len(non_framework_topics), 15, 20)

        return min(int(score), 100)

    def _score_ai_savviness(
        self,
        profile: dict[str, Any],
        commit_analysis: CommitAnalysisResult | None = None,
    ) -> int:
        """Score AI-savviness (0-100).

        V2: AI config detection, commit burst patterns, weighted factors.
        """
        score = 0.0
        repos = profile.get("repos", [])

        # AI-related topics (max 18 points)
        ai_topics = {
            "machine-learning",
            "deep-learning",
            "artificial-intelligence",
            "ai",
            "ml",
            "nlp",
            "llm",
            "gpt",
            "transformers",
            "neural-network",
            "computer-vision",
            "data-science",
            "chatgpt",
            "copilot",
            "generative-ai",
            "rag",
            "langchain",
            "openai",
            "huggingface",
            "stable-diffusion",
        }
        all_topics: set[str] = set()
        for repo in repos:
            all_topics.update(t.lower() for t in repo.get("topics", []))

        ai_topic_count = len(all_topics & ai_topics)
        score += _log_scale(ai_topic_count, 6, 18)

        # AI framework languages (max 12 points)
        ai_languages = {"Python", "Jupyter Notebook", "R", "Julia"}
        languages = profile.get("languages", [])
        if isinstance(languages, dict):
            lang_names = set(languages.keys())
        else:
            lang_names = {lang["name"] for lang in languages}
        ai_lang_count = len(lang_names & ai_languages)
        score += min(ai_lang_count / 2 * 12, 12)

        # AI repo names/descriptions (max 12 points)
        ai_name_patterns = re.compile(
            r"ai|ml|gpt|llm|neural|model|predict|classify"
            r"|detect|nlp|bert|transformer|diffusion|rag|agent",
            re.IGNORECASE,
        )
        ai_repos = sum(
            1
            for r in repos
            if ai_name_patterns.search(r.get("name", ""))
            or ai_name_patterns.search(r.get("description", "") or "")
        )
        score += _log_scale(ai_repos, 5, 12)

        # AI config file detection bonus (max 8 points)
        ai_config_score = self._detect_ai_config_files(repos)
        score += min(ai_config_score * 4, 8)

        # Commit analysis signals (max 35 points)
        if commit_analysis and commit_analysis.total_commits_analyzed > 0:
            # Direct AI tool mentions (max 18 points)
            total_mentions = sum(commit_analysis.ai_tool_mentions.values())
            mention_ratio = total_mentions / commit_analysis.total_commits_analyzed
            score += min(mention_ratio * 90, 18)

            # Co-author bot tags (max 10 points)
            total_bots = sum(commit_analysis.co_author_bots.values())
            bot_ratio = total_bots / commit_analysis.total_commits_analyzed
            score += min(bot_ratio * 50, 10)

            # Heuristic score contribution (max 5 points)
            score += min(commit_analysis.ai_heuristic_score / 20, 5)

            # Commit burst patterns (max 2 points)
            if commit_analysis.burst_score > 0:
                score += min(commit_analysis.burst_score * 2, 2)

        # Bonus for high AI repo ratio (max 15 points)
        if len(repos) > 0:
            ai_repo_ratio = ai_repos / len(repos)
            score += ai_repo_ratio * 15

        return min(int(score), 100)

    def _detect_ai_config_files(self, repos: list[dict[str, Any]]) -> int:
        """Detect AI config file indicators from repo metadata.

        Since we do not access file trees, uses heuristic detection
        based on repo topics and descriptions mentioning AI tool config.
        """
        ai_config_indicators = 0
        config_patterns = re.compile(
            r"copilot[- ]?instructions|cursorrules|\.aider"
            r"|codeium|tabnine|continue|windsurf",
            re.IGNORECASE,
        )
        for repo in repos:
            desc = repo.get("description", "") or ""
            name = repo.get("name", "")
            topics = " ".join(repo.get("topics", []))
            combined = f"{name} {desc} {topics}"
            if config_patterns.search(combined):
                ai_config_indicators += 1
        return ai_config_indicators

    def _classify_archetype(
        self, scores: dict[str, int], profile: dict[str, Any]
    ) -> dict[str, Any]:
        """Classify developer archetype based on weighted scoring.

        V2: Weighted scoring with requirement checks and ranked alternatives.
        """
        repos = profile.get("repos", [])
        languages = profile.get("languages", [])

        # Extract language names
        if isinstance(languages, dict):
            lang_names = set(languages.keys())
        else:
            lang_names = {lang.get("name", "") for lang in languages}

        # Collect all topics
        all_topics: set[str] = set()
        for repo in repos:
            all_topics.update(t.lower() for t in repo.get("topics", []))

        # Compute weighted score for each archetype
        archetype_scores: list[tuple[str, float, dict]] = []

        for archetype_id, archetype in ARCHETYPES.items():
            # Check requirements
            reqs = archetype.get("requires", {})
            if reqs.get("backend_langs") and not (lang_names & BACKEND_LANGUAGES):
                continue
            if reqs.get("frontend_langs") and not (lang_names & FRONTEND_LANGUAGES):
                continue
            if reqs.get("data_science_langs") and not (lang_names & DATA_SCIENCE_LANGUAGES):
                continue
            if reqs.get("devops_topics") and not (all_topics & DEVOPS_TOPICS):
                continue
            if reqs.get("security_topics") and not (all_topics & SECURITY_TOPICS):
                continue

            # Calculate weighted score (normalized by positive weight sum)
            weights = archetype["weights"]
            positive_sum = sum(w for w in weights.values() if w > 0)
            weighted = sum(
                scores.get(dim, 0) * weight for dim, weight in weights.items() if weight > 0
            )
            # Normalize so all archetypes produce comparable 0-100 range
            weighted = weighted / positive_sum if positive_sum > 0 else 0
            # Apply negative weights as penalties (unnormalized)
            for dim, weight in weights.items():
                if weight < 0:
                    weighted += scores.get(dim, 0) * weight

            if weighted >= archetype["min_score"]:
                archetype_scores.append((archetype_id, weighted, archetype))

        # Sort by weighted score (highest first)
        archetype_scores.sort(key=lambda x: x[1], reverse=True)

        if not archetype_scores:
            fallback = ARCHETYPES["code_explorer"]
            return {
                "id": "code_explorer",
                "name": fallback["name"],
                "description": fallback["description"],
                "confidence": 0.5,
                "alternatives": [],
            }

        primary_id, primary_score, primary = archetype_scores[0]

        # Confidence based on gap to second-best
        if len(archetype_scores) >= 2:
            gap = primary_score - archetype_scores[1][1]
            confidence = min(0.5 + gap / 40, 1.0)
        else:
            confidence = 0.9

        alternatives = [
            {"id": aid, "name": a["name"], "score": round(s, 1)}
            for aid, s, a in archetype_scores[1:4]
        ]

        return {
            "id": primary_id,
            "name": primary["name"],
            "description": primary["description"],
            "confidence": round(confidence, 2),
            "alternatives": alternatives,
        }

    def _analyze_ai_usage(
        self,
        profile: dict[str, Any],
        commit_analysis: CommitAnalysisResult | None = None,
    ) -> dict[str, Any]:
        """Analyze AI tool usage based on available data.

        V2: AI config detection, burst analysis, confidence scoring.
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
                if "windsurf" in topic_lower:
                    detected_tools.add("Windsurf")
                if "aider" in topic_lower:
                    detected_tools.add("Aider")

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
                "burst_score": commit_analysis.burst_score,
            }

        result: dict[str, Any] = {
            "overall_bucket": bucket,
            "detected_tools": sorted(detected_tools),
            "confidence": confidence,
            "ai_score": ai_score,
        }

        if commit_details:
            result["commit_analysis"] = commit_details
        else:
            result["note"] = (
                "Based on public repository metadata. Commit analysis available with GitHub token."
            )

        return result

    def _build_tech_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        """Build a summarized tech profile for prompt orchestration."""
        repos = profile.get("repos", [])
        languages = profile.get("languages", [])

        # Detect frameworks from repo topics
        framework_topics: set[str] = set()
        for repo in repos:
            framework_topics.update(t.lower() for t in repo.get("topics", []))

        detected_frameworks = sorted(framework_topics & KNOWN_FRAMEWORKS)

        # Top repos by stars
        top_repos = sorted(repos, key=lambda r: r.get("stars", 0), reverse=True)[:5]

        # Compute primary ecosystem
        if isinstance(languages, dict):
            lang_list = list(languages.keys())[:10]
        else:
            lang_list = [lang.get("name", "") for lang in languages[:10]]

        primary_ecosystem = self._detect_ecosystem(set(lang_list), set(detected_frameworks))

        return {
            "languages": lang_list,
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
            "primary_ecosystem": primary_ecosystem,
        }

    @staticmethod
    def _detect_ecosystem(languages: set[str], frameworks: set[str]) -> str:
        """Detect primary development ecosystem."""
        web_fws = {
            "react",
            "nextjs",
            "vue",
            "angular",
            "svelte",
            "remix",
            "nuxt",
            "astro",
        }
        backend_fws = {
            "fastapi",
            "django",
            "flask",
            "express",
            "nestjs",
            "spring",
            "rails",
            "laravel",
            "gin",
        }
        ml_fws = {"pytorch", "tensorflow", "langchain"}
        devops_tools = {"docker", "kubernetes", "terraform", "ansible"}

        if frameworks & ml_fws or languages & {"Jupyter Notebook", "R", "Julia"}:
            return "data-science"
        if frameworks & web_fws and frameworks & backend_fws:
            return "full-stack"
        if frameworks & web_fws:
            return "frontend"
        if frameworks & backend_fws:
            return "backend"
        if frameworks & devops_tools:
            return "devops"
        if languages & {"Python", "Java", "Go", "Rust", "C++"}:
            return "backend"
        if languages & {"TypeScript", "JavaScript"}:
            return "frontend"
        return "general"

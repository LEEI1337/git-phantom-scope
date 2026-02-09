"""Prompt Orchestrator - Context Engineering Layer.

Builds optimized prompts for different AI models based on profile data.
Implements context retrieval, processing, and management pipeline
based on "Survey on Context Engineering for LLMs" (2025).

Supports model-specific prompt formatting:
- Gemini: Natural language, descriptive style
- Stable Diffusion: Keywords, negative prompts
- FLUX.1: Concise descriptions
- OpenAI: Structured, role-based prompts
"""

from __future__ import annotations

from typing import Any, Optional

from app.logging_config import get_logger

logger = get_logger(__name__)


# Prompt templates for text generation (README)
README_TEMPLATES = {
    "professional": {
        "system": (
            "You are an expert tech writer specializing in GitHub profile READMEs. "
            "Create concise, professional, and visually appealing README content. "
            "Use markdown formatting with headers, badges, and tables. "
            "Do not include any fake or placeholder data."
        ),
        "user": (
            "Create a GitHub profile README for a {archetype_name} developer.\n\n"
            "Profile Summary:\n"
            "- Top Languages: {top_languages}\n"
            "- Frameworks: {frameworks}\n"
            "- Activity Score: {activity_score}/100\n"
            "- Collaboration Score: {collab_score}/100\n"
            "- Stack Diversity: {diversity_score}/100\n"
            "- AI Savviness: {ai_score}/100\n"
            "- Top Repositories: {top_repos}\n"
            "{career_goal_section}"
            "\nStyle: {style}\n"
            "Include: A brief intro, skills section, stats visualization placeholders, "
            "and a contact section. Keep it under 80 lines."
        ),
    },
    "creative": {
        "system": (
            "You are a creative developer branding specialist. "
            "Create eye-catching, personality-driven GitHub profile READMEs. "
            "Use emojis, creative headers, and engaging language. "
            "Make it stand out while remaining professional."
        ),
        "user": (
            "Create a creative GitHub profile README for a {archetype_name}.\n\n"
            "Developer Identity:\n"
            "- Core Stack: {top_languages}\n"
            "- Tools: {frameworks}\n"
            "- Archetype: {archetype_name} - {archetype_description}\n"
            "- Scores: Activity {activity_score}, Collab {collab_score}, "
            "Diversity {diversity_score}, AI {ai_score}\n"
            "- Best Work: {top_repos}\n"
            "{career_goal_section}"
            "\nMake it memorable and authentic."
        ),
    },
}

# Prompt templates for image generation
IMAGE_TEMPLATES = {
    "portfolio_banner": {
        "gemini": (
            "Create a minimalistic, dark-themed professional banner for a "
            "{archetype_name} developer profile. Visual style: {style}. "
            "Color palette: {colors}. Include abstract geometric symbols "
            "representing: {top_skills}. Clean, modern design. "
            "No text, no faces, no logos. 1584x396 pixels."
        ),
        "stable_diffusion": {
            "positive": (
                "minimalistic dark professional banner, abstract geometric art, "
                "developer portfolio, {style} style, {colors} color palette, "
                "symbols for {top_skills}, clean modern design, "
                "high quality, 4k, professional, sleek"
            ),
            "negative": (
                "text, words, letters, face, person, photo, realistic, "
                "busy, cluttered, low quality, blurry, watermark"
            ),
        },
        "flux": (
            "Minimalistic dark developer banner. {style} aesthetic. "
            "{colors} palette. Abstract symbols: {top_skills}. "
            "Clean, geometric, professional. No text. No faces."
        ),
    },
    "skill_wheel": {
        "gemini": (
            "Create an infographic-style skill wheel visualization for a "
            "{archetype_name}. Show proficiency levels for: {top_skills}. "
            "Color scheme: {colors}. Style: {style}. "
            "Circular/radar chart aesthetic. Dark background. "
            "Clean typography for skill labels. 1200x1200 pixels."
        ),
        "stable_diffusion": {
            "positive": (
                "infographic skill wheel, circular chart, data visualization, "
                "{style} design, {colors} colors, dark background, "
                "professional, clean, modern, high quality, 4k"
            ),
            "negative": (
                "photo, face, person, realistic, messy, cluttered, "
                "low quality, blurry, watermark, text heavy"
            ),
        },
        "flux": (
            "Skill wheel infographic. {style} design. {colors}. "
            "Circular data visualization. Dark background. "
            "Professional, clean, modern."
        ),
    },
    "social_card": {
        "gemini": (
            "Create a social media card (1200x630) for a {archetype_name} "
            "developer. Visual style: {style}. Colors: {colors}. "
            "Include abstract representations of: {top_skills}. "
            "Space for text overlay at top. Dark, professional. No text."
        ),
        "stable_diffusion": {
            "positive": (
                "social media card, developer profile, abstract tech art, "
                "{style} style, {colors} palette, professional, modern, "
                "clean layout, space for text, dark theme, high quality"
            ),
            "negative": (
                "text, words, face, person, cluttered, low quality, "
                "blurry, watermark, busy background"
            ),
        },
        "flux": (
            "Social card for {archetype_name}. {style}. {colors}. "
            "Abstract tech symbols: {top_skills}. Dark. Professional. "
            "Space for text overlay. No text."
        ),
    },
}


class PromptOrchestrator:
    """Context Engineering pipeline for AI model prompts."""

    def build_readme_prompt(
        self,
        scoring_result: dict[str, Any],
        profile: dict[str, Any],
        style: str = "professional",
        career_goal: Optional[str] = None,
    ) -> dict[str, str]:
        """Build a README generation prompt from scoring and profile data.

        Returns:
            Dict with 'system' and 'user' keys for model prompt.
        """
        template = README_TEMPLATES.get(style, README_TEMPLATES["professional"])
        tech_profile = scoring_result.get("tech_profile", {})
        scores = scoring_result.get("scores", {})
        archetype = scoring_result.get("archetype", {})

        # Context retrieval: extract most relevant data
        top_languages = ", ".join(
            l["name"] for l in tech_profile.get("languages", [])[:5]
        )
        frameworks = ", ".join(tech_profile.get("frameworks", [])[:8])
        top_repos = "; ".join(
            f"{r['name']} ({r.get('language', 'N/A')}, {r.get('stars', 0)} stars)"
            for r in tech_profile.get("top_repos", [])[:3]
        )

        career_goal_section = ""
        if career_goal:
            career_goal_section = f"- Career Goal: {career_goal}\n"

        # Context processing: format for model
        user_prompt = template["user"].format(
            archetype_name=archetype.get("name", "Developer"),
            archetype_description=archetype.get("description", ""),
            top_languages=top_languages or "Not specified",
            frameworks=frameworks or "Not specified",
            activity_score=scores.get("activity", 0),
            collab_score=scores.get("collaboration", 0),
            diversity_score=scores.get("stack_diversity", 0),
            ai_score=scores.get("ai_savviness", 0),
            top_repos=top_repos or "Not specified",
            career_goal_section=career_goal_section,
            style=style,
        )

        return {
            "system": template["system"],
            "user": user_prompt,
        }

    def build_image_prompt(
        self,
        scoring_result: dict[str, Any],
        template_id: str = "portfolio_banner",
        model_type: str = "gemini",
        style: str = "minimal",
        colors: Optional[list[str]] = None,
    ) -> str | dict[str, str]:
        """Build an image generation prompt.

        Args:
            scoring_result: Profile scoring data
            template_id: Image template to use
            model_type: Target model (gemini, stable_diffusion, flux)
            style: Visual style
            colors: Color palette hex codes

        Returns:
            Prompt string (gemini/flux) or dict with positive/negative (SD)
        """
        template_set = IMAGE_TEMPLATES.get(template_id, IMAGE_TEMPLATES["portfolio_banner"])
        template = template_set.get(model_type, template_set.get("gemini", ""))

        tech_profile = scoring_result.get("tech_profile", {})
        archetype = scoring_result.get("archetype", {})

        top_skills = ", ".join(
            l["name"] for l in tech_profile.get("languages", [])[:3]
        )
        color_str = ", ".join(colors) if colors else "#0D1117, #58A6FF, #238636"

        if isinstance(template, dict):
            # Stable Diffusion format
            return {
                "positive": template["positive"].format(
                    archetype_name=archetype.get("name", "Developer"),
                    top_skills=top_skills,
                    style=style,
                    colors=color_str,
                ),
                "negative": template["negative"],
            }
        else:
            return template.format(
                archetype_name=archetype.get("name", "Developer"),
                top_skills=top_skills,
                style=style,
                colors=color_str,
            )

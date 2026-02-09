"""Prompt Orchestrator - Context Engineering Layer.

Builds optimized prompts for different AI models based on profile data.
Implements context retrieval, processing, and management pipeline
based on "Survey on Context Engineering for LLMs" (2025).

Supports model-specific prompt formatting:
- Gemini: Natural language, descriptive style
- Stable Diffusion: Keywords, negative prompts
- FLUX.1: Concise descriptions
- OpenAI: Structured, role-based prompts

Template tiers:
- Free: portfolio_banner, skill_wheel, social_card (3 templates)
- Pro: All free + 10 premium templates (13 total)
"""

from __future__ import annotations

from typing import Any

from app.logging_config import get_logger

logger = get_logger(__name__)


# --- README TEMPLATES ---

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
        "tier": "free",
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
        "tier": "free",
    },
    "storyteller": {
        "system": (
            "You are a narrative designer who creates developer stories. "
            "Write a GitHub README that tells the developer's coding journey "
            "as a compelling narrative. Use metaphors from their archetype. "
            "Balance storytelling with useful technical information."
        ),
        "user": (
            "Write a story-driven GitHub README for a {archetype_name}.\n\n"
            "The Developer's Journey:\n"
            "- Languages mastered: {top_languages}\n"
            "- Arsenal: {frameworks}\n"
            "- Activity: {activity_score}/100, Collaboration: {collab_score}/100\n"
            "- Diversity: {diversity_score}/100, AI Savviness: {ai_score}/100\n"
            "- Flagship projects: {top_repos}\n"
            "{career_goal_section}"
            "\nStyle: narrative, engaging, use archetype-themed metaphors.\n"
            "Include markdown badges and a stats section. Under 100 lines."
        ),
        "tier": "pro",
    },
    "minimalist": {
        "system": (
            "You are a minimalist design expert. Create an ultra-clean GitHub "
            "README with maximum information density in minimum space. "
            "Use monospace elements, ASCII art dividers, and sparse formatting. "
            "Every word must earn its place."
        ),
        "user": (
            "Create a minimalist GitHub README for a {archetype_name}.\n\n"
            "Core data:\n"
            "- Stack: {top_languages} | {frameworks}\n"
            "- Metrics: A:{activity_score} C:{collab_score} "
            "D:{diversity_score} AI:{ai_score}\n"
            "- Work: {top_repos}\n"
            "{career_goal_section}"
            "\nRules: No emojis, minimal markdown, elegant simplicity. "
            "Under 40 lines."
        ),
        "tier": "pro",
    },
    "recruiter_ready": {
        "system": (
            "You are a tech recruiter advisor. Create a GitHub README optimized "
            "for hiring managers and technical recruiters. Emphasize measurable "
            "achievements, tech stack clarity, and professional presentation. "
            "Include sections recruiters look for."
        ),
        "user": (
            "Create a recruiter-optimized GitHub README for a {archetype_name}.\n\n"
            "Professional Profile:\n"
            "- Technical Stack: {top_languages}\n"
            "- Frameworks & Tools: {frameworks}\n"
            "- Activity Score: {activity_score}/100 (consistency indicator)\n"
            "- Collaboration Score: {collab_score}/100 (team player indicator)\n"
            "- Stack Diversity: {diversity_score}/100\n"
            "- AI Proficiency: {ai_score}/100\n"
            "- Key Projects: {top_repos}\n"
            "{career_goal_section}"
            "\nInclude: Summary, Skills Matrix, Featured Projects with impact "
            "metrics, Open Source Contributions, Contact/Availability section."
        ),
        "tier": "pro",
    },
}

# --- IMAGE TEMPLATES ---

IMAGE_TEMPLATES = {
    # === FREE TIER (3 templates) ===
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
        "tier": "free",
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
        "tier": "free",
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
        "tier": "free",
    },
    # === PRO TIER (10 premium templates) ===
    "neon_circuit": {
        "gemini": (
            "Create a neon-lit circuit board inspired banner for a "
            "{archetype_name}. Glowing traces in {colors} on dark PCB. "
            "Components represent: {top_skills}. Style: {style}. "
            "Cyberpunk tech aesthetic. 1584x396. No text, no faces."
        ),
        "stable_diffusion": {
            "positive": (
                "neon circuit board art, glowing traces, cyberpunk tech, "
                "PCB design, {style} style, {colors} neon glow, "
                "dark background, components for {top_skills}, "
                "high quality, 4k, ultradetailed, dramatic lighting"
            ),
            "negative": (
                "text, words, face, person, photo, realistic human, "
                "low quality, blurry, watermark, simple, flat"
            ),
        },
        "flux": (
            "Neon circuit board banner for {archetype_name}. "
            "Glowing {colors} traces on dark PCB. {top_skills} as components. "
            "{style}. Cyberpunk. No text. No faces."
        ),
        "tier": "pro",
    },
    "code_galaxy": {
        "gemini": (
            "Create a cosmic galaxy visualization where stars and nebulae "
            "represent programming skills for a {archetype_name}. "
            "Colors: {colors}. Each constellation maps to: {top_skills}. "
            "Style: {style}. 1584x396. No text, no faces."
        ),
        "stable_diffusion": {
            "positive": (
                "cosmic galaxy nebula, constellation art, programming universe, "
                "{style} style, {colors} nebula colors, space background, "
                "stars as code, {top_skills} constellations, "
                "high quality, 4k, beautiful, ethereal"
            ),
            "negative": (
                "text, words, face, person, planet earth, spaceship, "
                "low quality, blurry, watermark, cartoon"
            ),
        },
        "flux": (
            "Code galaxy banner. Cosmic nebulae as {top_skills}. "
            "{colors} palette. {style}. Constellations. Dark space. "
            "No text. No faces."
        ),
        "tier": "pro",
    },
    "isometric_workspace": {
        "gemini": (
            "Create an isometric 3D illustration of a developer workspace "
            "for a {archetype_name}. Include stylized monitors showing "
            "code in {top_skills}. Color palette: {colors}. "
            "Style: {style}. Low-poly aesthetic. 1584x396. No faces."
        ),
        "stable_diffusion": {
            "positive": (
                "isometric 3D workspace, developer desk, low poly art, "
                "monitors with code, {style} style, {colors} palette, "
                "{top_skills} themed objects, clean design, "
                "high quality, 4k, detailed miniature"
            ),
            "negative": (
                "text, words, face, person photo, realistic, messy, "
                "low quality, blurry, watermark, cluttered"
            ),
        },
        "flux": (
            "Isometric developer workspace. Low-poly 3D. {top_skills} themed. "
            "{colors}. {style}. Monitors and code. No faces. Clean."
        ),
        "tier": "pro",
    },
    "gradient_mesh": {
        "gemini": (
            "Create an abstract gradient mesh banner with flowing curves "
            "and layered depth for a {archetype_name}. "
            "Colors: {colors}. Inspired by: {top_skills}. "
            "Style: {style}. Smooth, modern, Apple-tier design. "
            "1584x396. No text, no faces."
        ),
        "stable_diffusion": {
            "positive": (
                "abstract gradient mesh, flowing curves, layered depth, "
                "modern design, {style} style, {colors} gradients, "
                "smooth transitions, Apple aesthetic, premium, "
                "high quality, 4k, beautiful, elegant"
            ),
            "negative": (
                "text, words, face, person, sharp edges, pixelated, "
                "low quality, blurry, watermark, busy"
            ),
        },
        "flux": (
            "Abstract gradient mesh banner. Flowing curves. {colors}. "
            "{style}. Modern, premium. Smooth depth layers. "
            "No text. No faces."
        ),
        "tier": "pro",
    },
    "terminal_retro": {
        "gemini": (
            "Create a retro terminal/CRT screen aesthetic banner for a "
            "{archetype_name}. Green-on-black or {colors} phosphor glow. "
            "Matrix-style cascading symbols for: {top_skills}. "
            "Style: {style}. Scanlines, CRT curve. 1584x396. No faces."
        ),
        "stable_diffusion": {
            "positive": (
                "retro CRT terminal, green phosphor glow, matrix rain, "
                "hacker aesthetic, {style} style, {colors} on black, "
                "scanlines, vintage computer, {top_skills} symbols, "
                "high quality, 4k, atmospheric, moody"
            ),
            "negative": (
                "face, person, modern UI, color photo, realistic, "
                "low quality, blurry, watermark, bright colorful"
            ),
        },
        "flux": (
            "Retro CRT terminal banner. {colors} phosphor on black. "
            "Matrix-style {top_skills} symbols. {style}. "
            "Scanlines. Vintage. No faces."
        ),
        "tier": "pro",
    },
    "hexagonal_grid": {
        "gemini": (
            "Create a hexagonal grid/honeycomb pattern banner for a "
            "{archetype_name}. Each hex cell contains an icon for: "
            "{top_skills}. Color scheme: {colors}. Style: {style}. "
            "Dark background, subtle glow. 1584x396. No text, no faces."
        ),
        "stable_diffusion": {
            "positive": (
                "hexagonal grid, honeycomb pattern, tech icons, "
                "{style} style, {colors} palette, dark background, "
                "subtle glow, {top_skills} icons in hexagons, "
                "high quality, 4k, geometric, precise"
            ),
            "negative": (
                "text, words, face, person, organic shapes, low quality, blurry, watermark, messy"
            ),
        },
        "flux": (
            "Hexagonal grid banner. Honeycomb with {top_skills} icons. "
            "{colors}. {style}. Dark, glowing edges. "
            "No text. No faces."
        ),
        "tier": "pro",
    },
    "data_flow": {
        "gemini": (
            "Create a data flow / pipeline visualization banner for a "
            "{archetype_name}. Abstract data streams connecting nodes "
            "representing: {top_skills}. Colors: {colors}. "
            "Style: {style}. Network topology aesthetic. "
            "1584x396. No text, no faces."
        ),
        "stable_diffusion": {
            "positive": (
                "data flow visualization, network nodes, pipeline art, "
                "{style} style, {colors} data streams, dark background, "
                "connecting lines, {top_skills} node icons, "
                "high quality, 4k, technical, elegant"
            ),
            "negative": (
                "text, words, face, person, chart labels, axis numbers, "
                "low quality, blurry, watermark, simple"
            ),
        },
        "flux": (
            "Data flow pipeline banner. Network nodes for {top_skills}. "
            "{colors} streams. {style}. Abstract topology. "
            "No text. No faces."
        ),
        "tier": "pro",
    },
    "topographic": {
        "gemini": (
            "Create a topographic contour map style banner for a "
            "{archetype_name}. Elevation lines form abstract shapes "
            "suggesting: {top_skills}. Colors: {colors}. "
            "Style: {style}. Geographic art meets tech. "
            "1584x396. No text, no faces."
        ),
        "stable_diffusion": {
            "positive": (
                "topographic contour map, elevation lines, geographic art, "
                "{style} style, {colors} lines on dark, "
                "abstract landscape, {top_skills} terrain shapes, "
                "high quality, 4k, detailed linework, elegant"
            ),
            "negative": (
                "text, words, face, person, real photo, satellite, "
                "low quality, blurry, watermark, colorful"
            ),
        },
        "flux": (
            "Topographic contour banner. Abstract elevation lines. "
            "{colors} on dark. {top_skills} shapes. {style}. "
            "Geographic. No text. No faces."
        ),
        "tier": "pro",
    },
    "blueprint": {
        "gemini": (
            "Create a technical blueprint style banner for a "
            "{archetype_name}. White/light lines on blue grid background. "
            "Schematics of: {top_skills}. Colors: {colors}. "
            "Style: {style}. Engineering drawing aesthetic. "
            "1584x396. No faces."
        ),
        "stable_diffusion": {
            "positive": (
                "technical blueprint, engineering drawing, white lines on blue, "
                "{style} style, grid background, {colors} accents, "
                "schematics for {top_skills}, design document, "
                "high quality, 4k, precise, technical"
            ),
            "negative": (
                "face, person, photo, realistic, messy handwriting, "
                "low quality, blurry, watermark, colorful art"
            ),
        },
        "flux": (
            "Blueprint banner. White lines on blue grid. "
            "{top_skills} schematics. {colors} accents. {style}. "
            "Engineering drawing. No faces."
        ),
        "tier": "pro",
    },
    "particle_wave": {
        "gemini": (
            "Create a particle wave / audio waveform inspired banner for a "
            "{archetype_name}. Dynamic particles forming waves that represent: "
            "{top_skills}. Colors: {colors}. Style: {style}. "
            "Motion blur, energy visualization. 1584x396. No text, no faces."
        ),
        "stable_diffusion": {
            "positive": (
                "particle wave, audio waveform art, dynamic particles, "
                "{style} style, {colors} particle glow, dark background, "
                "energy visualization, {top_skills} wave patterns, "
                "high quality, 4k, motion blur, vivid"
            ),
            "negative": (
                "text, words, face, person, static, flat, low quality, blurry, watermark, simple"
            ),
        },
        "flux": (
            "Particle wave banner. Dynamic energy particles. "
            "{colors} glow. {top_skills} wave patterns. {style}. "
            "Motion. Dark background. No text. No faces."
        ),
        "tier": "pro",
    },
}

# Template tier classification
FREE_TEMPLATES = {k for k, v in IMAGE_TEMPLATES.items() if v.get("tier") == "free"}
PRO_TEMPLATES = {k for k, v in IMAGE_TEMPLATES.items() if v.get("tier") == "pro"}
ALL_TEMPLATES = FREE_TEMPLATES | PRO_TEMPLATES


class PromptOrchestrator:
    """Context Engineering pipeline for AI model prompts."""

    def build_readme_prompt(
        self,
        scoring_result: dict[str, Any],
        profile: dict[str, Any],
        style: str = "professional",
        career_goal: str | None = None,
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
        top_languages = ", ".join(l["name"] for l in tech_profile.get("languages", [])[:5])
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
        colors: list[str] | None = None,
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

        top_skills = ", ".join(l["name"] for l in tech_profile.get("languages", [])[:3])
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
        return template.format(
            archetype_name=archetype.get("name", "Developer"),
            top_skills=top_skills,
            style=style,
            colors=color_str,
        )

    @staticmethod
    def get_available_templates(tier: str = "free") -> list[str]:
        """Get template IDs available for a given tier.

        Args:
            tier: 'free', 'pro', or 'enterprise'

        Returns:
            List of available template IDs.
        """
        if tier in ("pro", "enterprise"):
            return sorted(ALL_TEMPLATES)
        return sorted(FREE_TEMPLATES)

    @staticmethod
    def get_available_readme_styles(tier: str = "free") -> list[str]:
        """Get README style names available for a given tier."""
        if tier in ("pro", "enterprise"):
            return sorted(README_TEMPLATES.keys())
        return [
            k for k in sorted(README_TEMPLATES.keys()) if README_TEMPLATES[k].get("tier") == "free"
        ]

    @staticmethod
    def is_template_allowed(template_id: str, tier: str) -> bool:
        """Check if a template is allowed for the given tier."""
        if tier in ("pro", "enterprise"):
            return template_id in ALL_TEMPLATES
        return template_id in FREE_TEMPLATES

    @staticmethod
    def is_readme_style_allowed(style: str, tier: str) -> bool:
        """Check if a README style is allowed for the given tier."""
        if tier in ("pro", "enterprise"):
            return style in README_TEMPLATES
        template = README_TEMPLATES.get(style)
        return template is not None and template.get("tier") == "free"

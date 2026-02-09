"""Tests for PromptOrchestrator."""

import pytest

from services.prompt_orchestrator import IMAGE_TEMPLATES, README_TEMPLATES, PromptOrchestrator


@pytest.fixture
def orchestrator():
    return PromptOrchestrator()


@pytest.fixture
def sample_scoring_result():
    return {
        "scores": {
            "activity": 75,
            "collaboration": 60,
            "stack_diversity": 80,
            "ai_savviness": 90,
        },
        "archetype": {
            "name": "AI-Driven Indie Hacker",
            "description": "High AI usage with strong solo output",
            "confidence": 0.85,
        },
        "tech_profile": {
            "languages": [
                {"name": "Python", "percentage": 45.0},
                {"name": "TypeScript", "percentage": 30.0},
                {"name": "Go", "percentage": 15.0},
            ],
            "frameworks": ["FastAPI", "React", "Next.js", "TensorFlow"],
            "top_repos": [
                {"name": "my-app", "language": "Python", "stars": 42},
                {"name": "web-ui", "language": "TypeScript", "stars": 15},
            ],
        },
    }


@pytest.fixture
def sample_profile():
    return {
        "username": "testdev",
        "name": "Test Developer",
        "public_repos": 30,
    }


class TestReadmePromptBuilding:
    def test_build_readme_prompt_professional(self, orchestrator, sample_scoring_result):
        result = orchestrator.build_readme_prompt(
            scoring_result=sample_scoring_result,
            profile=sample_scoring_result.get("tech_profile", {}),
            style="professional",
        )

        assert "system" in result
        assert "user" in result
        assert "AI-Driven Indie Hacker" in result["user"]
        assert "Python" in result["user"]
        assert "75" in result["user"]  # activity score

    def test_build_readme_prompt_creative(self, orchestrator, sample_scoring_result):
        result = orchestrator.build_readme_prompt(
            scoring_result=sample_scoring_result,
            profile={},
            style="creative",
        )

        assert "system" in result
        assert "creative" in result["system"].lower()
        assert "AI-Driven Indie Hacker" in result["user"]

    def test_build_readme_prompt_with_career_goal(self, orchestrator, sample_scoring_result):
        result = orchestrator.build_readme_prompt(
            scoring_result=sample_scoring_result,
            profile={},
            career_goal="Become a Staff Engineer",
        )

        assert "Become a Staff Engineer" in result["user"]

    def test_build_readme_prompt_unknown_style_falls_back(
        self, orchestrator, sample_scoring_result
    ):
        result = orchestrator.build_readme_prompt(
            scoring_result=sample_scoring_result,
            profile={},
            style="nonexistent",
        )

        # Falls back to professional template
        assert "system" in result
        assert "user" in result

    def test_build_readme_prompt_empty_tech_profile(self, orchestrator):
        result = orchestrator.build_readme_prompt(
            scoring_result={"scores": {}, "archetype": {}, "tech_profile": {}},
            profile={},
        )

        assert "Not specified" in result["user"]


class TestImagePromptBuilding:
    def test_build_image_prompt_gemini(self, orchestrator, sample_scoring_result):
        result = orchestrator.build_image_prompt(
            scoring_result=sample_scoring_result,
            template_id="portfolio_banner",
            model_type="gemini",
        )

        assert isinstance(result, str)
        assert "AI-Driven Indie Hacker" in result

    def test_build_image_prompt_stable_diffusion(self, orchestrator, sample_scoring_result):
        result = orchestrator.build_image_prompt(
            scoring_result=sample_scoring_result,
            template_id="portfolio_banner",
            model_type="stable_diffusion",
        )

        assert isinstance(result, dict)
        assert "positive" in result
        assert "negative" in result

    def test_build_image_prompt_flux(self, orchestrator, sample_scoring_result):
        result = orchestrator.build_image_prompt(
            scoring_result=sample_scoring_result,
            template_id="portfolio_banner",
            model_type="flux",
        )

        assert isinstance(result, str)

    def test_build_image_prompt_skill_wheel(self, orchestrator, sample_scoring_result):
        result = orchestrator.build_image_prompt(
            scoring_result=sample_scoring_result,
            template_id="skill_wheel",
            model_type="gemini",
        )

        assert isinstance(result, str)
        assert "skill" in result.lower() or "wheel" in result.lower()

    def test_build_image_prompt_social_card(self, orchestrator, sample_scoring_result):
        result = orchestrator.build_image_prompt(
            scoring_result=sample_scoring_result,
            template_id="social_card",
            model_type="gemini",
        )

        assert isinstance(result, str)
        assert "social" in result.lower()

    def test_build_image_prompt_custom_colors(self, orchestrator, sample_scoring_result):
        result = orchestrator.build_image_prompt(
            scoring_result=sample_scoring_result,
            template_id="portfolio_banner",
            model_type="gemini",
            colors=["#FF0000", "#00FF00"],
        )

        assert "#FF0000" in result

    def test_build_image_prompt_unknown_template_falls_back(
        self, orchestrator, sample_scoring_result
    ):
        result = orchestrator.build_image_prompt(
            scoring_result=sample_scoring_result,
            template_id="nonexistent",
            model_type="gemini",
        )

        # Falls back to portfolio_banner
        assert isinstance(result, str)


class TestTemplateStructure:
    def test_readme_templates_have_required_keys(self):
        for style, template in README_TEMPLATES.items():
            assert "system" in template, f"Missing 'system' in {style}"
            assert "user" in template, f"Missing 'user' in {style}"

    def test_image_templates_have_all_models(self):
        for template_id, templates in IMAGE_TEMPLATES.items():
            assert "gemini" in templates, f"Missing 'gemini' in {template_id}"
            assert "stable_diffusion" in templates, f"Missing 'stable_diffusion' in {template_id}"
            assert "flux" in templates, f"Missing 'flux' in {template_id}"

    def test_sd_templates_have_positive_negative(self):
        for _template_id, templates in IMAGE_TEMPLATES.items():
            sd = templates["stable_diffusion"]
            assert isinstance(sd, dict)
            assert "positive" in sd
            assert "negative" in sd

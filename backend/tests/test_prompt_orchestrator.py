"""Tests for PromptOrchestrator."""

import pytest

from services.prompt_orchestrator import (
    ALL_TEMPLATES,
    FREE_TEMPLATES,
    IMAGE_TEMPLATES,
    PRO_TEMPLATES,
    README_TEMPLATES,
    PromptOrchestrator,
)


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


class TestTierClassification:
    def test_free_templates_count(self):
        assert len(FREE_TEMPLATES) == 3

    def test_pro_templates_count(self):
        assert len(PRO_TEMPLATES) == 10

    def test_all_templates_is_union(self):
        assert ALL_TEMPLATES == FREE_TEMPLATES | PRO_TEMPLATES

    def test_free_templates_known(self):
        expected_free = {"portfolio_banner", "skill_wheel", "social_card"}
        assert expected_free == FREE_TEMPLATES

    def test_pro_templates_known(self):
        assert "neon_circuit" in PRO_TEMPLATES
        assert "code_galaxy" in PRO_TEMPLATES
        assert "isometric_workspace" in PRO_TEMPLATES
        assert "gradient_mesh" in PRO_TEMPLATES
        assert "terminal_retro" in PRO_TEMPLATES
        assert "hexagonal_grid" in PRO_TEMPLATES
        assert "data_flow" in PRO_TEMPLATES
        assert "topographic" in PRO_TEMPLATES
        assert "blueprint" in PRO_TEMPLATES
        assert "particle_wave" in PRO_TEMPLATES

    def test_all_image_templates_classified(self):
        for template_id in IMAGE_TEMPLATES:
            assert template_id in ALL_TEMPLATES, f"{template_id} not classified"

    def test_image_templates_have_tier_field(self):
        for template_id, templates in IMAGE_TEMPLATES.items():
            assert "tier" in templates, f"Missing tier in {template_id}"
            assert templates["tier"] in ("free", "pro")

    def test_readme_templates_have_tier_field(self):
        for style, template in README_TEMPLATES.items():
            assert "tier" in template, f"Missing tier in {style}"
            assert template["tier"] in ("free", "pro")


class TestTierHelpers:
    def test_get_available_templates_free(self):
        templates = PromptOrchestrator.get_available_templates("free")
        assert set(templates) == FREE_TEMPLATES

    def test_get_available_templates_pro(self):
        templates = PromptOrchestrator.get_available_templates("pro")
        assert set(templates) == ALL_TEMPLATES

    def test_get_available_templates_enterprise(self):
        templates = PromptOrchestrator.get_available_templates("enterprise")
        assert set(templates) == ALL_TEMPLATES

    def test_get_available_readme_styles_free(self):
        styles = PromptOrchestrator.get_available_readme_styles("free")
        assert "professional" in styles
        assert "creative" in styles
        assert "storyteller" not in styles

    def test_get_available_readme_styles_pro(self):
        styles = PromptOrchestrator.get_available_readme_styles("pro")
        assert len(styles) == 5
        assert "storyteller" in styles
        assert "minimalist" in styles
        assert "recruiter_ready" in styles

    def test_is_template_allowed_free_template_on_free(self):
        assert PromptOrchestrator.is_template_allowed("portfolio_banner", "free") is True

    def test_is_template_allowed_pro_template_on_free(self):
        assert PromptOrchestrator.is_template_allowed("neon_circuit", "free") is False

    def test_is_template_allowed_pro_template_on_pro(self):
        assert PromptOrchestrator.is_template_allowed("neon_circuit", "pro") is True

    def test_is_readme_style_allowed_pro_on_free(self):
        assert PromptOrchestrator.is_readme_style_allowed("storyteller", "free") is False

    def test_is_readme_style_allowed_pro_on_pro(self):
        assert PromptOrchestrator.is_readme_style_allowed("storyteller", "pro") is True

    def test_is_readme_style_allowed_free_on_free(self):
        assert PromptOrchestrator.is_readme_style_allowed("professional", "free") is True


class TestProTemplatePrompts:
    @pytest.fixture
    def sample_scoring_result(self):
        return {
            "scores": {
                "activity": 85,
                "collaboration": 70,
                "stack_diversity": 90,
                "ai_savviness": 95,
            },
            "archetype": {
                "name": "Full-Stack Polyglot",
                "description": "Diverse tech stack mastery",
                "confidence": 0.92,
            },
            "tech_profile": {
                "languages": [
                    {"name": "Python", "percentage": 35.0},
                    {"name": "TypeScript", "percentage": 25.0},
                    {"name": "Rust", "percentage": 20.0},
                ],
                "frameworks": ["FastAPI", "React", "Next.js"],
                "top_repos": [
                    {"name": "polyglot-app", "language": "Python", "stars": 100},
                ],
            },
        }

    def test_neon_circuit_gemini(self, sample_scoring_result):
        orch = PromptOrchestrator()
        result = orch.build_image_prompt(
            scoring_result=sample_scoring_result,
            template_id="neon_circuit",
            model_type="gemini",
        )
        assert isinstance(result, str)
        assert len(result) > 50

    def test_code_galaxy_sd(self, sample_scoring_result):
        orch = PromptOrchestrator()
        result = orch.build_image_prompt(
            scoring_result=sample_scoring_result,
            template_id="code_galaxy",
            model_type="stable_diffusion",
        )
        assert isinstance(result, dict)
        assert "positive" in result
        assert "negative" in result

    def test_blueprint_flux(self, sample_scoring_result):
        orch = PromptOrchestrator()
        result = orch.build_image_prompt(
            scoring_result=sample_scoring_result,
            template_id="blueprint",
            model_type="flux",
        )
        assert isinstance(result, str)

    def test_storyteller_readme(self, sample_scoring_result):
        orch = PromptOrchestrator()
        result = orch.build_readme_prompt(
            scoring_result=sample_scoring_result,
            profile={},
            style="storyteller",
        )
        assert "system" in result
        assert "user" in result

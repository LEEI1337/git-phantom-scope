"""Tests for ImageGenerator pipeline orchestration."""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from services.image_generator import ImageGenerator


def _create_test_image_bytes() -> bytes:
    img = Image.new("RGBA", (400, 200), (13, 17, 23, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


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
            ],
            "frameworks": ["FastAPI", "React"],
            "top_repos": [
                {"name": "my-app", "language": "Python", "stars": 42},
            ],
        },
    }


class TestImageGeneratorInit:
    def test_creates_with_dependencies(self):
        gen = ImageGenerator()
        assert gen.prompt_orchestrator is not None
        assert gen.renderer is not None
        assert gen.packager is not None


class TestFallbackReadme:
    def test_fallback_readme_content(self, sample_scoring_result):
        result = ImageGenerator._fallback_readme(sample_scoring_result)
        assert "AI-Driven Indie Hacker" in result
        assert "Python" in result
        assert "75" in result

    def test_fallback_readme_empty_scoring(self):
        result = ImageGenerator._fallback_readme(
            {"scores": {}, "archetype": {}, "tech_profile": {}}
        )
        assert "Developer" in result
        assert "N/A" in result


class TestProviderMapping:
    def test_gemini_mapping(self):
        assert ImageGenerator._provider_to_model_type("gemini") == "gemini"

    def test_openai_mapping(self):
        assert ImageGenerator._provider_to_model_type("openai") == "gemini"

    def test_sd_mapping(self):
        assert ImageGenerator._provider_to_model_type("stable_diffusion") == "stable_diffusion"

    def test_flux_mapping(self):
        assert ImageGenerator._provider_to_model_type("flux") == "flux"

    def test_unknown_defaults_to_gemini(self):
        assert ImageGenerator._provider_to_model_type("unknown") == "gemini"


class TestGeneratePipeline:
    @pytest.mark.asyncio
    async def test_generate_readme_only(self, sample_scoring_result):
        gen = ImageGenerator()

        mock_connector = AsyncMock()
        mock_connector.generate_text.return_value = "# Generated README"

        mock_storage = AsyncMock()
        mock_storage.store.return_value = "/api/v1/public/generate/test-id/download"

        with (
            patch.object(gen, "_get_connector", return_value=mock_connector),
            patch("services.asset_storage.AssetStorage", return_value=mock_storage),
        ):
            result = await gen.generate(
                job_id="test-id",
                scoring_result=sample_scoring_result,
                requested_assets=["readme"],
                api_key="test-key",
            )

        assert "download_url" in result
        assert "completed_assets" in result
        assert "readme" in result["completed_assets"]

    @pytest.mark.asyncio
    async def test_generate_with_banner(self, sample_scoring_result):
        gen = ImageGenerator()
        test_image = _create_test_image_bytes()

        mock_connector = AsyncMock()
        mock_connector.generate_text.return_value = "# README"
        mock_connector.generate_image.return_value = test_image

        mock_storage = AsyncMock()
        mock_storage.store.return_value = "/download/url"

        with (
            patch.object(gen, "_get_connector", return_value=mock_connector),
            patch("services.asset_storage.AssetStorage", return_value=mock_storage),
        ):
            result = await gen.generate(
                job_id="test-id",
                scoring_result=sample_scoring_result,
                requested_assets=["readme", "banner"],
                api_key="test-key",
            )

        assert "banner" in result["completed_assets"]
        assert "readme" in result["completed_assets"]

    @pytest.mark.asyncio
    async def test_generate_without_api_key_uses_fallback_readme(self, sample_scoring_result):
        gen = ImageGenerator()

        mock_storage = AsyncMock()
        mock_storage.store.return_value = "/download/url"

        settings = MagicMock()
        settings.gemini_shared_key = None

        with (
            patch("app.config.get_settings", return_value=settings),
            patch("services.asset_storage.AssetStorage", return_value=mock_storage),
        ):
            result = await gen.generate(
                job_id="test-id",
                scoring_result=sample_scoring_result,
                requested_assets=["readme"],
            )

        assert "readme" in result["completed_assets"]

    @pytest.mark.asyncio
    async def test_generate_progress_callback(self, sample_scoring_result):
        gen = ImageGenerator()

        progress_values = []

        mock_connector = AsyncMock()
        mock_connector.generate_text.return_value = "# README"

        mock_storage = AsyncMock()
        mock_storage.store.return_value = "/download/url"

        with (
            patch.object(gen, "_get_connector", return_value=mock_connector),
            patch("services.asset_storage.AssetStorage", return_value=mock_storage),
        ):
            await gen.generate(
                job_id="test-id",
                scoring_result=sample_scoring_result,
                requested_assets=["readme"],
                api_key="test-key",
                progress_callback=lambda p: progress_values.append(p),
            )

        assert len(progress_values) > 0
        assert progress_values[-1] >= 90  # Should reach near completion

"""Image Generation Pipeline Orchestrator.

Coordinates the full generation flow:
PromptOrchestrator → ModelConnector → Renderer → Packager → AssetStorage

Manages progress updates, error handling, and fallback strategies.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.exceptions import GenerationError, ModelProviderError
from app.logging_config import get_logger
from app.metrics import GENERATION_DURATION, GENERATIONS_TOTAL

logger = get_logger(__name__)


class ImageGenerator:
    """Orchestrates profile package generation."""

    def __init__(self) -> None:
        from services.model_connector import get_connector
        from services.packager import Packager, Renderer
        from services.prompt_orchestrator import PromptOrchestrator

        self.prompt_orchestrator = PromptOrchestrator()
        self.renderer = Renderer()
        self.packager = Packager()
        self._get_connector = get_connector

    async def generate(
        self,
        job_id: str,
        scoring_result: dict[str, Any],
        requested_assets: list[str],
        template_id: str = "portfolio_banner",
        model_preferences: dict[str, str] | None = None,
        api_key: str | None = None,
        tier: str = "free",
        progress_callback: Callable[[int], None] | None = None,
    ) -> dict[str, Any]:
        """Generate a complete profile package.

        Args:
            job_id: Unique job identifier for tracking
            scoring_result: Profile scoring data from scoring engine
            requested_assets: List of assets to generate (readme, banner, social_cards)
            template_id: Image template ID (portfolio_banner, skill_wheel, social_card)
            model_preferences: Provider preferences (text_model, image_model)
            api_key: BYOK API key (decrypted, in-memory only)
            tier: User tier (free, pro, enterprise) — affects watermark
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with download_url and completed_assets info
        """
        import time

        start_time = time.perf_counter()
        prefs = model_preferences or {}
        text_provider = prefs.get("text_model", "gemini").split("-")[0]
        image_provider = prefs.get("image_model", "gemini").split("-")[0]
        completed_assets: dict[str, str] = {}

        def _progress(pct: int) -> None:
            if progress_callback:
                progress_callback(pct)

        try:
            _progress(15)

            # --- Step 1: Generate README ---
            readme_content = ""
            if "readme" in requested_assets:
                readme_content = await self._generate_readme(
                    scoring_result=scoring_result,
                    provider=text_provider,
                    api_key=api_key,
                )
                completed_assets["readme"] = "README.md"
                logger.info("readme_generated", job_id=job_id)
            _progress(35)

            # --- Step 2: Generate banner image ---
            banner_image: bytes | None = None
            if "banner" in requested_assets:
                banner_image = await self._generate_image(
                    scoring_result=scoring_result,
                    template_id=template_id,
                    provider=image_provider,
                    api_key=api_key,
                    tier=tier,
                )
                completed_assets["banner"] = "profile-banner.png"
                logger.info("banner_generated", job_id=job_id)
            _progress(60)

            # --- Step 3: Generate social cards ---
            social_cards: dict[str, bytes] = {}
            if "social_cards" in requested_assets:
                social_cards = await self._generate_social_cards(
                    scoring_result=scoring_result,
                    provider=image_provider,
                    api_key=api_key,
                    tier=tier,
                )
                for platform in social_cards:
                    completed_assets[f"social_{platform}"] = f"social-cards/{platform}.png"
                logger.info(
                    "social_cards_generated",
                    job_id=job_id,
                    count=len(social_cards),
                )
            _progress(80)

            # --- Step 4: Create ZIP bundle ---
            bundle_bytes = self.packager.create_bundle(
                readme_content=readme_content or self._fallback_readme(scoring_result),
                banner_image=banner_image,
                social_cards=social_cards if social_cards else None,
            )
            _progress(90)

            # --- Step 5: Store bundle temporarily ---
            from services.asset_storage import AssetStorage

            storage = AssetStorage()
            download_url = await storage.store(job_id=job_id, data=bundle_bytes)
            _progress(95)

            # Record metrics
            duration = time.perf_counter() - start_time
            GENERATION_DURATION.labels(template=template_id).observe(duration)
            GENERATIONS_TOTAL.labels(template=template_id, tier=tier, status="success").inc()

            logger.info(
                "generation_complete",
                job_id=job_id,
                duration=f"{duration:.2f}s",
                assets=list(completed_assets.keys()),
            )

            return {
                "download_url": download_url,
                "completed_assets": completed_assets,
            }

        except ModelProviderError:
            GENERATIONS_TOTAL.labels(template=template_id, tier=tier, status="model_error").inc()
            raise
        except Exception as exc:
            GENERATIONS_TOTAL.labels(template=template_id, tier=tier, status="error").inc()
            logger.error("generation_failed", job_id=job_id, error=str(exc))
            raise GenerationError("Profile generation failed") from exc

    async def _generate_readme(
        self,
        scoring_result: dict[str, Any],
        provider: str = "gemini",
        api_key: str | None = None,
    ) -> str:
        """Generate README.md content using AI model."""
        prompt = self.prompt_orchestrator.build_readme_prompt(
            scoring_result=scoring_result,
            profile=scoring_result.get("tech_profile", {}),
        )

        connector = self._get_connector(provider)

        # Use BYOK key or shared key for free tier
        key = api_key
        if not key:
            from app.config import get_settings

            settings = get_settings()
            if settings.gemini_shared_key:
                key = settings.gemini_shared_key.get_secret_value()

        if not key:
            logger.warning("no_api_key_available", provider=provider)
            return self._fallback_readme(scoring_result)

        try:
            return await connector.generate_text(prompt=prompt, api_key=key)
        except ModelProviderError:
            logger.warning("readme_generation_failed_using_fallback", provider=provider)
            return self._fallback_readme(scoring_result)

    async def _generate_image(
        self,
        scoring_result: dict[str, Any],
        template_id: str,
        provider: str = "gemini",
        api_key: str | None = None,
        tier: str = "free",
    ) -> bytes:
        """Generate a single image asset."""
        model_type = self._provider_to_model_type(provider)
        prompt = self.prompt_orchestrator.build_image_prompt(
            scoring_result=scoring_result,
            template_id=template_id,
            model_type=model_type,
        )

        connector = self._get_connector(provider)

        key = api_key
        if not key:
            from app.config import get_settings

            settings = get_settings()
            if settings.gemini_shared_key:
                key = settings.gemini_shared_key.get_secret_value()

        if not key:
            raise GenerationError("No API key available for image generation")

        image_bytes = await connector.generate_image(prompt=prompt, api_key=key)

        # Apply watermark based on tier
        return self.renderer.add_watermark(image_bytes, tier=tier)

    async def _generate_social_cards(
        self,
        scoring_result: dict[str, Any],
        provider: str = "gemini",
        api_key: str | None = None,
        tier: str = "free",
    ) -> dict[str, bytes]:
        """Generate social media cards for multiple platforms."""
        cards: dict[str, bytes] = {}
        platforms = ["github", "linkedin", "twitter"]

        for platform in platforms:
            try:
                image = await self._generate_image(
                    scoring_result=scoring_result,
                    template_id="social_card",
                    provider=provider,
                    api_key=api_key,
                    tier=tier,
                )
                cards[platform] = image
            except (ModelProviderError, GenerationError):
                logger.warning(
                    "social_card_generation_failed",
                    platform=platform,
                )
                # Continue with other platforms — partial success is acceptable
                continue

        return cards

    @staticmethod
    def _provider_to_model_type(provider: str) -> str:
        """Map provider name to prompt template model type."""
        mapping = {
            "gemini": "gemini",
            "openai": "gemini",  # OpenAI uses similar natural language prompts
            "sd": "stable_diffusion",
            "stable_diffusion": "stable_diffusion",
            "flux": "flux",
        }
        return mapping.get(provider, "gemini")

    @staticmethod
    def _fallback_readme(scoring_result: dict[str, Any]) -> str:
        """Generate a basic README without AI when no API key is available."""
        archetype = scoring_result.get("archetype", {})
        scores = scoring_result.get("scores", {})
        tech = scoring_result.get("tech_profile", {})

        languages = ", ".join(lang["name"] for lang in tech.get("languages", [])[:5])
        frameworks = ", ".join(tech.get("frameworks", [])[:5])

        return f"""# Developer Profile

## {archetype.get("name", "Developer")}

{archetype.get("description", "")}

## Tech Stack

**Languages:** {languages or "N/A"}
**Frameworks:** {frameworks or "N/A"}

## Scores

| Dimension | Score |
|-----------|-------|
| Activity | {scores.get("activity", 0)}/100 |
| Collaboration | {scores.get("collaboration", 0)}/100 |
| Stack Diversity | {scores.get("stack_diversity", 0)}/100 |
| AI Savviness | {scores.get("ai_savviness", 0)}/100 |

---
*Generated by [Git Phantom Scope](https://gitphantomscope.dev)*
*Privacy-First — No data was stored during generation.*
"""

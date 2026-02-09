"""Multi-Provider AI Model Connector with BYOK Support.

Manages connections to multiple AI providers (Gemini, OpenAI, SD, FLUX).
Supports Bring Your Own Key (BYOK) pattern where user-provided keys
are decrypted in-memory only for the duration of the API call.

SECURITY:
- Keys are NEVER logged, stored to disk, or persisted in any way
- Keys exist in memory only during the API call execution
- Error messages NEVER contain key values
"""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.exceptions import InvalidBYOKKeyError, ModelProviderError
from app.logging_config import get_logger
from app.metrics import MODEL_CALL_DURATION, MODEL_CALLS

logger = get_logger(__name__)


class BaseModelConnector(ABC):
    """Abstract base class for AI model connectors."""

    provider: str = ""

    @abstractmethod
    async def validate_key(self, api_key: str) -> dict[str, Any]:
        """Validate an API key and return tier info."""
        ...

    @abstractmethod
    async def generate_text(self, prompt: dict[str, str], api_key: str) -> str:
        """Generate text from a prompt."""
        ...

    @abstractmethod
    async def generate_image(
        self, prompt: str | dict[str, str], api_key: str, **kwargs: Any
    ) -> bytes:
        """Generate an image from a prompt."""
        ...


class GeminiConnector(BaseModelConnector):
    """Google Gemini API connector (supports free tier)."""

    provider = "gemini"

    async def validate_key(self, api_key: str) -> dict[str, Any]:
        """Validate Gemini API key."""
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params={"key": api_key})

            if response.status_code == 200:
                return {
                    "valid": True,
                    "tier": "free",
                    "rate_limits": {
                        "requests_per_minute": 15,
                        "requests_per_day": 1500,
                    },
                    "features": {
                        "text_generation": True,
                        "image_generation": True,
                    },
                }
            raise InvalidBYOKKeyError("gemini")
        except httpx.RequestError:
            raise ModelProviderError("gemini", "Gemini API unreachable")

    async def generate_text(self, prompt: dict[str, str], api_key: str) -> str:
        """Generate text using Gemini API."""
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt.get("user", "")}],
                    "role": "user",
                }
            ],
            "systemInstruction": {"parts": [{"text": prompt.get("system", "")}]},
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            },
        }

        try:
            with MODEL_CALL_DURATION.labels(provider="gemini", model="gemini-2.0-flash").time():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, json=payload, params={"key": api_key})

            MODEL_CALLS.labels(
                provider="gemini",
                model="gemini-2.0-flash",
                type="text",
                status=str(response.status_code),
            ).inc()

            if response.status_code != 200:
                raise ModelProviderError("gemini", "Text generation failed")

            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")

            raise ModelProviderError("gemini", "Empty response from Gemini")

        except httpx.RequestError:
            MODEL_CALLS.labels(
                provider="gemini", model="gemini-2.0-flash", type="text", status="error"
            ).inc()
            raise ModelProviderError("gemini", "Gemini API connection failed")

    async def generate_image(
        self, prompt: str | dict[str, str], api_key: str, **kwargs: Any
    ) -> bytes:
        """Generate image using Gemini Imagen API."""
        url = "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict"

        prompt_text = prompt if isinstance(prompt, str) else prompt.get("positive", "")

        payload = {
            "instances": [{"prompt": prompt_text}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": kwargs.get("aspect_ratio", "16:9"),
            },
        }

        try:
            with MODEL_CALL_DURATION.labels(provider="gemini", model="imagen-3").time():
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(url, json=payload, params={"key": api_key})

            MODEL_CALLS.labels(
                provider="gemini", model="imagen-3", type="image", status=str(response.status_code)
            ).inc()

            if response.status_code != 200:
                raise ModelProviderError("gemini", "Image generation failed")

            data = response.json()
            predictions = data.get("predictions", [])
            if predictions:
                image_b64 = predictions[0].get("bytesBase64Encoded", "")
                return base64.b64decode(image_b64)

            raise ModelProviderError("gemini", "No image generated")

        except httpx.RequestError:
            MODEL_CALLS.labels(
                provider="gemini", model="imagen-3", type="image", status="error"
            ).inc()
            raise ModelProviderError("gemini", "Gemini Imagen API connection failed")


class OpenAIConnector(BaseModelConnector):
    """OpenAI API connector (GPT-4, DALL-E 3)."""

    provider = "openai"

    async def validate_key(self, api_key: str) -> dict[str, Any]:
        """Validate OpenAI API key."""
        url = "https://api.openai.com/v1/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
            if response.status_code == 200:
                return {
                    "valid": True,
                    "tier": "pro",
                    "rate_limits": {
                        "requests_per_minute": 60,
                        "requests_per_day": 10000,
                    },
                    "features": {
                        "text_generation": True,
                        "image_generation": True,
                    },
                }
            raise InvalidBYOKKeyError("openai")
        except httpx.RequestError:
            raise ModelProviderError("openai", "OpenAI API unreachable")

    async def generate_text(self, prompt: dict[str, str], api_key: str) -> str:
        """Generate text using OpenAI GPT API."""
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": prompt.get("system", "")},
                {"role": "user", "content": prompt.get("user", "")},
            ],
            "temperature": 0.7,
            "max_tokens": 2048,
        }

        try:
            with MODEL_CALL_DURATION.labels(provider="openai", model="gpt-4o").time():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        url,
                        json=payload,
                        headers={"Authorization": f"Bearer {api_key}"},
                    )

            MODEL_CALLS.labels(
                provider="openai", model="gpt-4o", type="text", status=str(response.status_code)
            ).inc()

            if response.status_code != 200:
                raise ModelProviderError("openai", "Text generation failed")

            data = response.json()
            return data["choices"][0]["message"]["content"]

        except httpx.RequestError:
            MODEL_CALLS.labels(provider="openai", model="gpt-4o", type="text", status="error").inc()
            raise ModelProviderError("openai", "OpenAI API connection failed")

    async def generate_image(
        self, prompt: str | dict[str, str], api_key: str, **kwargs: Any
    ) -> bytes:
        """Generate image using DALL-E 3."""
        url = "https://api.openai.com/v1/images/generations"
        prompt_text = prompt if isinstance(prompt, str) else prompt.get("positive", "")

        payload = {
            "model": "dall-e-3",
            "prompt": prompt_text,
            "n": 1,
            "size": kwargs.get("size", "1792x1024"),
            "quality": kwargs.get("quality", "standard"),
            "response_format": "b64_json",
        }

        try:
            with MODEL_CALL_DURATION.labels(provider="openai", model="dall-e-3").time():
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        url,
                        json=payload,
                        headers={"Authorization": f"Bearer {api_key}"},
                    )

            MODEL_CALLS.labels(
                provider="openai", model="dall-e-3", type="image", status=str(response.status_code)
            ).inc()

            if response.status_code != 200:
                raise ModelProviderError("openai", "Image generation failed")

            data = response.json()
            image_b64 = data["data"][0]["b64_json"]
            return base64.b64decode(image_b64)

        except httpx.RequestError:
            MODEL_CALLS.labels(
                provider="openai", model="dall-e-3", type="image", status="error"
            ).inc()
            raise ModelProviderError("openai", "OpenAI API connection failed")


class StableDiffusionConnector(BaseModelConnector):
    """Stable Diffusion connector (self-hosted via Automatic1111/ComfyUI API).

    Connects to a self-hosted SD WebUI (AUTOMATIC1111) or ComfyUI instance.
    Requires the user to provide their own endpoint URL as the "api_key"
    (format: "http://host:port" or "http://host:port|optional_auth_token").
    """

    provider = "stable_diffusion"

    def _parse_endpoint(self, api_key: str) -> tuple[str, str | None]:
        """Parse endpoint URL and optional auth token from api_key field.

        Formats:
          - "http://localhost:7860"
          - "http://localhost:7860|my-auth-token"
        """
        if "|" in api_key:
            endpoint, token = api_key.split("|", 1)
            return endpoint.rstrip("/"), token
        return api_key.rstrip("/"), None

    async def validate_key(self, api_key: str) -> dict[str, Any]:
        """Validate SD endpoint connectivity."""
        endpoint, token = self._parse_endpoint(api_key)
        url = f"{endpoint}/sdapi/v1/sd-models"
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 200:
                models = response.json()
                return {
                    "valid": True,
                    "tier": "pro",
                    "rate_limits": {
                        "requests_per_minute": 10,
                        "requests_per_day": 1000,
                    },
                    "features": {
                        "text_generation": False,
                        "image_generation": True,
                        "available_models": len(models),
                    },
                }
            raise InvalidBYOKKeyError("stable_diffusion")
        except httpx.RequestError:
            raise ModelProviderError("stable_diffusion", "Stable Diffusion API unreachable")

    async def generate_text(self, prompt: dict[str, str], api_key: str) -> str:
        """SD does not support text generation."""
        raise ModelProviderError(
            "stable_diffusion",
            "Stable Diffusion does not support text generation",
        )

    async def generate_image(
        self, prompt: str | dict[str, str], api_key: str, **kwargs: Any
    ) -> bytes:
        """Generate image using Stable Diffusion txt2img API."""
        endpoint, token = self._parse_endpoint(api_key)
        url = f"{endpoint}/sdapi/v1/txt2img"

        if isinstance(prompt, dict):
            positive = prompt.get("positive", "")
            negative = prompt.get("negative", "")
        else:
            positive = prompt
            negative = ""

        payload = {
            "prompt": positive,
            "negative_prompt": negative,
            "steps": kwargs.get("steps", 30),
            "cfg_scale": kwargs.get("cfg_scale", 7.0),
            "width": kwargs.get("width", 1024),
            "height": kwargs.get("height", 576),
            "sampler_name": kwargs.get("sampler", "DPM++ 2M Karras"),
            "batch_size": 1,
            "n_iter": 1,
        }

        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            with MODEL_CALL_DURATION.labels(provider="stable_diffusion", model="sd-webui").time():
                async with httpx.AsyncClient(timeout=300.0) as client:
                    response = await client.post(url, json=payload, headers=headers)

            MODEL_CALLS.labels(
                provider="stable_diffusion",
                model="sd-webui",
                type="image",
                status=str(response.status_code),
            ).inc()

            if response.status_code != 200:
                raise ModelProviderError("stable_diffusion", "Image generation failed")

            data = response.json()
            images = data.get("images", [])
            if not images:
                raise ModelProviderError("stable_diffusion", "No image generated")
            return base64.b64decode(images[0])

        except httpx.RequestError:
            MODEL_CALLS.labels(
                provider="stable_diffusion",
                model="sd-webui",
                type="image",
                status="error",
            ).inc()
            raise ModelProviderError("stable_diffusion", "Stable Diffusion API connection failed")


class FluxConnector(BaseModelConnector):
    """FLUX.1 connector (via Replicate, fal.ai, or self-hosted).

    Supports FLUX.1-schnell (fast) and FLUX.1-dev (quality) models.
    API key format: "provider:api_key" where provider is replicate or fal.
    Default provider is replicate.
    """

    provider = "flux"

    def _parse_provider(self, api_key: str) -> tuple[str, str]:
        """Parse provider prefix from API key.

        Formats:
          - "replicate:r8_xxxxx"  -> ("replicate", "r8_xxxxx")
          - "fal:fal_xxxxx"      -> ("fal", "fal_xxxxx")
          - "r8_xxxxx"           -> ("replicate", "r8_xxxxx") (default)
        """
        if ":" in api_key and api_key.split(":", 1)[0] in ("replicate", "fal"):
            provider, key = api_key.split(":", 1)
            return provider, key
        return "replicate", api_key

    async def validate_key(self, api_key: str) -> dict[str, Any]:
        """Validate FLUX API key (via Replicate or fal.ai)."""
        provider, key = self._parse_provider(api_key)

        if provider == "replicate":
            url = "https://api.replicate.com/v1/account"
            headers = {"Authorization": f"Bearer {key}"}
        else:  # fal
            url = "https://rest.alpha.fal.ai/auth/current"
            headers = {"Authorization": f"Key {key}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 200:
                return {
                    "valid": True,
                    "tier": "pro",
                    "rate_limits": {
                        "requests_per_minute": 30,
                        "requests_per_day": 5000,
                    },
                    "features": {
                        "text_generation": False,
                        "image_generation": True,
                        "models": ["flux-schnell", "flux-dev"],
                    },
                }
            raise InvalidBYOKKeyError("flux")
        except httpx.RequestError:
            raise ModelProviderError("flux", "FLUX API unreachable")

    async def generate_text(self, prompt: dict[str, str], api_key: str) -> str:
        """FLUX does not support text generation."""
        raise ModelProviderError("flux", "FLUX does not support text generation")

    async def generate_image(
        self, prompt: str | dict[str, str], api_key: str, **kwargs: Any
    ) -> bytes:
        """Generate image using FLUX.1 via Replicate or fal.ai."""
        provider, key = self._parse_provider(api_key)
        prompt_text = prompt if isinstance(prompt, str) else prompt.get("positive", "")

        model_variant = kwargs.get("model", "schnell")  # schnell or dev

        if provider == "replicate":
            return await self._generate_replicate(prompt_text, key, model_variant, **kwargs)
        return await self._generate_fal(prompt_text, key, model_variant, **kwargs)

    async def _generate_replicate(
        self, prompt: str, api_key: str, variant: str, **kwargs: Any
    ) -> bytes:
        """Generate via Replicate predictions API."""
        model_map = {
            "schnell": "black-forest-labs/flux-schnell",
            "dev": "black-forest-labs/flux-dev",
        }
        model_id = model_map.get(variant, model_map["schnell"])
        url = "https://api.replicate.com/v1/predictions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_id,
            "input": {
                "prompt": prompt,
                "width": kwargs.get("width", 1024),
                "height": kwargs.get("height", 576),
                "num_outputs": 1,
                "output_format": "png",
            },
        }

        try:
            with MODEL_CALL_DURATION.labels(provider="flux", model=f"flux-{variant}").time():
                async with httpx.AsyncClient(timeout=120.0) as client:
                    # Create prediction
                    response = await client.post(url, json=payload, headers=headers)

                    if response.status_code not in (200, 201):
                        raise ModelProviderError("flux", "Prediction creation failed")

                    prediction = response.json()
                    poll_url = prediction.get("urls", {}).get("get", "")

                    if not poll_url:
                        raise ModelProviderError("flux", "No poll URL returned")

                    # Poll for completion (max ~120s)
                    import asyncio

                    for _ in range(60):
                        await asyncio.sleep(2)
                        poll_resp = await client.get(poll_url, headers=headers)
                        if poll_resp.status_code != 200:
                            continue
                        poll_data = poll_resp.json()
                        status = poll_data.get("status")

                        if status == "succeeded":
                            output = poll_data.get("output", [])
                            if not output:
                                raise ModelProviderError("flux", "No image output")
                            # Download the image
                            img_resp = await client.get(output[0])
                            MODEL_CALLS.labels(
                                provider="flux",
                                model=f"flux-{variant}",
                                type="image",
                                status="200",
                            ).inc()
                            return img_resp.content

                        if status == "failed":
                            raise ModelProviderError("flux", "Generation failed")

                    raise ModelProviderError("flux", "Generation timed out")

        except httpx.RequestError:
            MODEL_CALLS.labels(
                provider="flux",
                model=f"flux-{variant}",
                type="image",
                status="error",
            ).inc()
            raise ModelProviderError("flux", "FLUX API connection failed")

    async def _generate_fal(self, prompt: str, api_key: str, variant: str, **kwargs: Any) -> bytes:
        """Generate via fal.ai serverless API."""
        model_map = {
            "schnell": "fal-ai/flux/schnell",
            "dev": "fal-ai/flux/dev",
        }
        model_path = model_map.get(variant, model_map["schnell"])
        url = f"https://fal.run/{model_path}"
        headers = {
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "prompt": prompt,
            "image_size": {
                "width": kwargs.get("width", 1024),
                "height": kwargs.get("height", 576),
            },
            "num_images": 1,
        }

        try:
            with MODEL_CALL_DURATION.labels(provider="flux", model=f"flux-{variant}").time():
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(url, json=payload, headers=headers)

            MODEL_CALLS.labels(
                provider="flux",
                model=f"flux-{variant}",
                type="image",
                status=str(response.status_code),
            ).inc()

            if response.status_code != 200:
                raise ModelProviderError("flux", "Image generation failed")

            data = response.json()
            images = data.get("images", [])
            if not images:
                raise ModelProviderError("flux", "No image generated")

            # fal returns image URL — download it
            img_url = images[0].get("url", "")
            if not img_url:
                raise ModelProviderError("flux", "No image URL returned")

            async with httpx.AsyncClient(timeout=30.0) as client:
                img_resp = await client.get(img_url)
            return img_resp.content

        except httpx.RequestError:
            MODEL_CALLS.labels(
                provider="flux",
                model=f"flux-{variant}",
                type="image",
                status="error",
            ).inc()
            raise ModelProviderError("flux", "FLUX API connection failed")


# Provider registry
PROVIDERS: dict[str, type[BaseModelConnector]] = {
    "gemini": GeminiConnector,
    "openai": OpenAIConnector,
    "stable_diffusion": StableDiffusionConnector,
    "flux": FluxConnector,
}


def get_connector(provider: str) -> BaseModelConnector:
    """Get a model connector instance by provider name."""
    connector_class = PROVIDERS.get(provider)
    if not connector_class:
        raise ModelProviderError(provider, f"Unknown provider: {provider}")
    return connector_class()

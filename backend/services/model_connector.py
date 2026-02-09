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
from typing import Any, Optional

import httpx

from app.config import get_settings
from app.exceptions import InvalidBYOKKeyError, ModelProviderError
from app.logging_config import get_logger
from app.metrics import MODEL_CALLS, MODEL_CALL_DURATION

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
            else:
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
            "systemInstruction": {
                "parts": [{"text": prompt.get("system", "")}]
            },
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            },
        }

        try:
            with MODEL_CALL_DURATION.labels(provider="gemini", model="gemini-2.0-flash").time():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        url, json=payload, params={"key": api_key}
                    )

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
                    response = await client.post(
                        url, json=payload, params={"key": api_key}
                    )

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
                response = await client.get(
                    url, headers={"Authorization": f"Bearer {api_key}"}
                )
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
            MODEL_CALLS.labels(
                provider="openai", model="gpt-4o", type="text", status="error"
            ).inc()
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


# Provider registry
PROVIDERS: dict[str, type[BaseModelConnector]] = {
    "gemini": GeminiConnector,
    "openai": OpenAIConnector,
}


def get_connector(provider: str) -> BaseModelConnector:
    """Get a model connector instance by provider name."""
    connector_class = PROVIDERS.get(provider)
    if not connector_class:
        raise ModelProviderError(provider, f"Unknown provider: {provider}")
    return connector_class()

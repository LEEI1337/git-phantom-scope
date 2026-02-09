"""Tests for model_connector providers."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.exceptions import InvalidBYOKKeyError, ModelProviderError
from services.model_connector import (
    PROVIDERS,
    FluxConnector,
    GeminiConnector,
    OpenAIConnector,
    StableDiffusionConnector,
    get_connector,
)


class TestProviderRegistry:
    def test_gemini_registered(self):
        assert "gemini" in PROVIDERS

    def test_openai_registered(self):
        assert "openai" in PROVIDERS

    def test_get_connector_gemini(self):
        connector = get_connector("gemini")
        assert isinstance(connector, GeminiConnector)

    def test_get_connector_openai(self):
        connector = get_connector("openai")
        assert isinstance(connector, OpenAIConnector)

    def test_get_connector_unknown_raises(self):
        with pytest.raises(ModelProviderError):
            get_connector("unknown_provider")


class TestGeminiConnector:
    @pytest.mark.asyncio
    async def test_validate_key_success(self):
        connector = GeminiConnector()
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await connector.validate_key("test-key")

        assert result["valid"] is True
        assert result["tier"] == "free"

    @pytest.mark.asyncio
    async def test_validate_key_invalid(self):
        connector = GeminiConnector()
        mock_response = AsyncMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(InvalidBYOKKeyError):
                await connector.validate_key("bad-key")

    @pytest.mark.asyncio
    async def test_validate_key_network_error(self):
        connector = GeminiConnector()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.RequestError("Network error")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(ModelProviderError):
                await connector.validate_key("key")

    @pytest.mark.asyncio
    async def test_generate_text_success(self):
        connector = GeminiConnector()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Generated text content"}],
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await connector.generate_text(
                prompt={"system": "You are helpful", "user": "Generate text"},
                api_key="key",
            )

        assert result == "Generated text content"


class TestOpenAIConnector:
    @pytest.mark.asyncio
    async def test_validate_key_success(self):
        connector = OpenAIConnector()
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await connector.validate_key("sk-test-key")

        assert result["valid"] is True
        assert result["tier"] == "pro"

    @pytest.mark.asyncio
    async def test_validate_key_invalid(self):
        connector = OpenAIConnector()
        mock_response = AsyncMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(InvalidBYOKKeyError):
                await connector.validate_key("bad-key")


class TestStableDiffusionConnector:
    def test_parse_endpoint_simple(self):
        connector = StableDiffusionConnector()
        endpoint, token = connector._parse_endpoint("http://localhost:7860")
        assert endpoint == "http://localhost:7860"
        assert token is None

    def test_parse_endpoint_with_token(self):
        connector = StableDiffusionConnector()
        endpoint, token = connector._parse_endpoint("http://localhost:7860|my-auth")
        assert endpoint == "http://localhost:7860"
        assert token == "my-auth"  # noqa: S105

    def test_parse_endpoint_strips_trailing_slash(self):
        connector = StableDiffusionConnector()
        endpoint, _ = connector._parse_endpoint("http://host:7860/")
        assert endpoint == "http://host:7860"

    @pytest.mark.asyncio
    async def test_validate_key_success(self):
        connector = StableDiffusionConnector()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"title": "model_v1"}, {"title": "model_v2"}]

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await connector.validate_key("http://localhost:7860")

        assert result["valid"] is True
        assert result["features"]["image_generation"] is True
        assert result["features"]["text_generation"] is False
        assert result["features"]["available_models"] == 2

    @pytest.mark.asyncio
    async def test_validate_key_unreachable(self):
        connector = StableDiffusionConnector()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.RequestError("Connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(ModelProviderError):
                await connector.validate_key("http://localhost:7860")

    @pytest.mark.asyncio
    async def test_generate_text_raises(self):
        connector = StableDiffusionConnector()
        with pytest.raises(ModelProviderError, match="text generation"):
            await connector.generate_text(
                prompt={"system": "test", "user": "test"}, api_key="http://localhost:7860"
            )

    @pytest.mark.asyncio
    async def test_generate_image_with_dict_prompt(self):
        connector = StableDiffusionConnector()
        import base64

        fake_image = b"\x89PNG\r\n" + b"\x00" * 100
        b64_image = base64.b64encode(fake_image).decode()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"images": [b64_image]}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await connector.generate_image(
                prompt={"positive": "a cat", "negative": "blurry"},
                api_key="http://localhost:7860",
            )

        assert result == fake_image

    def test_sd_registered_in_providers(self):
        assert "stable_diffusion" in PROVIDERS

    def test_get_connector_sd(self):
        connector = get_connector("stable_diffusion")
        assert isinstance(connector, StableDiffusionConnector)


class TestFluxConnector:
    def test_parse_provider_replicate_prefix(self):
        connector = FluxConnector()
        provider, key = connector._parse_provider("replicate:r8_xxxxx")
        assert provider == "replicate"
        assert key == "r8_xxxxx"

    def test_parse_provider_fal_prefix(self):
        connector = FluxConnector()
        provider, key = connector._parse_provider("fal:fal_xxxxx")
        assert provider == "fal"
        assert key == "fal_xxxxx"

    def test_parse_provider_default_replicate(self):
        connector = FluxConnector()
        provider, key = connector._parse_provider("r8_no_prefix_key")
        assert provider == "replicate"
        assert key == "r8_no_prefix_key"

    @pytest.mark.asyncio
    async def test_validate_key_replicate_success(self):
        connector = FluxConnector()
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await connector.validate_key("replicate:r8_test")

        assert result["valid"] is True
        assert "flux-schnell" in result["features"]["models"]

    @pytest.mark.asyncio
    async def test_validate_key_fal_success(self):
        connector = FluxConnector()
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await connector.validate_key("fal:fal_test")

        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_key_invalid(self):
        connector = FluxConnector()
        mock_response = AsyncMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(InvalidBYOKKeyError):
                await connector.validate_key("replicate:bad_key")

    @pytest.mark.asyncio
    async def test_generate_text_raises(self):
        connector = FluxConnector()
        with pytest.raises(ModelProviderError, match="text generation"):
            await connector.generate_text(
                prompt={"system": "test", "user": "test"}, api_key="replicate:key"
            )

    def test_flux_registered_in_providers(self):
        assert "flux" in PROVIDERS

    def test_get_connector_flux(self):
        connector = get_connector("flux")
        assert isinstance(connector, FluxConnector)

    def test_all_four_providers_registered(self):
        assert len(PROVIDERS) == 4
        expected = {"gemini", "openai", "stable_diffusion", "flux"}
        assert set(PROVIDERS.keys()) == expected

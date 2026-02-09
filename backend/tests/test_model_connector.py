"""Tests for model_connector providers."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.exceptions import InvalidBYOKKeyError, ModelProviderError
from services.model_connector import (
    PROVIDERS,
    GeminiConnector,
    OpenAIConnector,
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

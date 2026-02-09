"""
Git Phantom Scope — White-Label Configuration Service.

Enterprise feature: allows customers to customize branding,
colors, logos, and domain for their own branded instance.

Privacy: white-label config is stored per org_id in Redis (TTL 24h)
or PostgreSQL (for persistent enterprise accounts).
"""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.config import get_settings
from app.exceptions import GPSBaseError


class WhiteLabelError(GPSBaseError):
    """White-label configuration error."""

    def __init__(self, message: str = "White-label configuration error") -> None:
        super().__init__(
            code="WHITE_LABEL_ERROR",
            message=message,
            status_code=400,
        )


class BrandTheme(str, Enum):
    """Available brand themes."""

    DARK = "dark"
    LIGHT = "light"
    CUSTOM = "custom"


class WhiteLabelConfig(BaseModel):
    """White-label branding configuration."""

    org_id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    company_name: str = Field(..., min_length=1, max_length=128)
    logo_url: str | None = Field(None, max_length=512)
    favicon_url: str | None = Field(None, max_length=512)
    custom_domain: str | None = Field(None, max_length=253)
    theme: BrandTheme = BrandTheme.DARK
    primary_color: str = Field("#58A6FF", pattern=r"^#[0-9a-fA-F]{6}$")
    secondary_color: str = Field("#238636", pattern=r"^#[0-9a-fA-F]{6}$")
    accent_color: str = Field("#8B5CF6", pattern=r"^#[0-9a-fA-F]{6}$")
    background_color: str = Field("#0D1117", pattern=r"^#[0-9a-fA-F]{6}$")
    surface_color: str = Field("#161B22", pattern=r"^#[0-9a-fA-F]{6}$")
    text_color: str = Field("#C9D1D9", pattern=r"^#[0-9a-fA-F]{6}$")
    font_family: str = Field("Inter, system-ui, sans-serif", max_length=128)
    footer_text: str | None = Field(None, max_length=256)
    hide_powered_by: bool = False
    custom_css: str | None = Field(None, max_length=4096)
    watermark_text: str | None = Field(None, max_length=64)
    email_from_name: str | None = Field(None, max_length=128)
    email_from_address: str | None = Field(None, max_length=254)

    @field_validator("custom_domain")
    @classmethod
    def validate_domain(cls, v: str | None) -> str | None:
        if v is None:
            return v
        pattern = r"^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid domain format")
        return v.lower()

    @field_validator("custom_css")
    @classmethod
    def sanitize_css(cls, v: str | None) -> str | None:
        if v is None:
            return v
        dangerous_patterns = [
            r"javascript\s*:",
            r"expression\s*\(",
            r"url\s*\(\s*['\"]?\s*javascript",
            r"@import",
            r"behavior\s*:",
            r"-moz-binding",
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("CSS contains potentially dangerous content")
        return v


_REDIS_PREFIX = "whitelabel:"
_CONFIG_TTL = 86400  # 24 hours


class WhiteLabelService:
    """Manages white-label configurations for enterprise customers."""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client
        self._settings = get_settings()

    async def save_config(self, config: WhiteLabelConfig) -> dict[str, str]:
        """Save white-label configuration to Redis."""
        key = f"{_REDIS_PREFIX}{config.org_id}"
        data = config.model_dump(mode="json")
        await self._redis.setex(key, _CONFIG_TTL, json.dumps(data))
        return {"status": "saved", "org_id": config.org_id}

    async def get_config(self, org_id: str) -> WhiteLabelConfig | None:
        """Retrieve white-label configuration."""
        key = f"{_REDIS_PREFIX}{org_id}"
        raw = await self._redis.get(key)
        if raw is None:
            return None
        data = json.loads(raw)
        return WhiteLabelConfig.model_validate(data)

    async def delete_config(self, org_id: str) -> bool:
        """Delete white-label configuration."""
        key = f"{_REDIS_PREFIX}{org_id}"
        result = await self._redis.delete(key)
        return result > 0

    async def get_css_variables(self, org_id: str) -> dict[str, str]:
        """Generate CSS custom properties from white-label config."""
        config = await self.get_config(org_id)
        if config is None:
            return _default_css_vars()
        return {
            "--gps-bg": config.background_color,
            "--gps-surface": config.surface_color,
            "--gps-border": "#30363D",
            "--gps-text": config.text_color,
            "--gps-accent": config.primary_color,
            "--gps-green": config.secondary_color,
            "--gps-purple": config.accent_color,
            "--gps-font": config.font_family,
        }

    async def get_branding(self, org_id: str) -> dict[str, Any]:
        """Get full branding info for frontend rendering."""
        config = await self.get_config(org_id)
        if config is None:
            return _default_branding()
        return {
            "company_name": config.company_name,
            "logo_url": config.logo_url,
            "favicon_url": config.favicon_url,
            "theme": config.theme.value,
            "css_variables": await self.get_css_variables(org_id),
            "footer_text": config.footer_text,
            "hide_powered_by": config.hide_powered_by,
            "custom_css": config.custom_css,
            "watermark_text": config.watermark_text,
        }

    async def list_configs(self) -> list[str]:
        """List all org IDs with white-label configs."""
        pattern = f"{_REDIS_PREFIX}*"
        keys: list[bytes] = []
        async for key in self._redis.scan_iter(match=pattern):  # type: ignore[union-attr]
            keys.append(key)
        prefix_len = len(_REDIS_PREFIX)
        return [k.decode()[prefix_len:] if isinstance(k, bytes) else k[prefix_len:] for k in keys]


def _default_css_vars() -> dict[str, str]:
    """Default Git Phantom Scope CSS variables."""
    return {
        "--gps-bg": "#0D1117",
        "--gps-surface": "#161B22",
        "--gps-border": "#30363D",
        "--gps-text": "#C9D1D9",
        "--gps-accent": "#58A6FF",
        "--gps-green": "#238636",
        "--gps-purple": "#8B5CF6",
        "--gps-font": "Inter, system-ui, sans-serif",
    }


def _default_branding() -> dict[str, Any]:
    """Default Git Phantom Scope branding."""
    return {
        "company_name": "Git Phantom Scope",
        "logo_url": None,
        "favicon_url": None,
        "theme": "dark",
        "css_variables": _default_css_vars(),
        "footer_text": None,
        "hide_powered_by": False,
        "custom_css": None,
        "watermark_text": "Git Phantom Scope",
    }

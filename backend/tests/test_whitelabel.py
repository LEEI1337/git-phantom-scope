"""Tests for White-Label Configuration Service."""

import fakeredis.aioredis
import pytest
from pydantic import ValidationError

from services.whitelabel import (
    BrandTheme,
    WhiteLabelConfig,
    WhiteLabelError,
    WhiteLabelService,
    _default_branding,
    _default_css_vars,
)


@pytest.fixture
async def fake_redis():
    server = fakeredis.FakeServer()
    redis = fakeredis.aioredis.FakeRedis(server=server)
    yield redis
    await redis.close()


@pytest.fixture
def service(fake_redis):
    return WhiteLabelService(fake_redis)


@pytest.fixture
def sample_config():
    return WhiteLabelConfig(
        org_id="acme-corp",
        company_name="ACME Corporation",
        logo_url="https://acme.com/logo.png",
        favicon_url="https://acme.com/favicon.ico",
        custom_domain="analytics.acme.com",
        theme=BrandTheme.DARK,
        primary_color="#FF6B35",
        secondary_color="#004E89",
        accent_color="#FFD166",
        background_color="#1A1A2E",
        surface_color="#16213E",
        text_color="#E0E0E0",
        font_family="Roboto, sans-serif",
        footer_text="Powered by ACME Analytics",
        hide_powered_by=True,
        watermark_text="ACME Analytics",
    )


# --- WhiteLabelConfig Model Tests ---


class TestWhiteLabelConfig:
    def test_valid_config(self, sample_config):
        assert sample_config.org_id == "acme-corp"
        assert sample_config.company_name == "ACME Corporation"
        assert sample_config.theme == BrandTheme.DARK

    def test_minimal_config(self):
        config = WhiteLabelConfig(org_id="test", company_name="Test")
        assert config.primary_color == "#58A6FF"
        assert config.hide_powered_by is False
        assert config.theme == BrandTheme.DARK

    def test_invalid_org_id_empty(self):
        with pytest.raises(ValidationError):
            WhiteLabelConfig(org_id="", company_name="Test")

    def test_invalid_org_id_special_chars(self):
        with pytest.raises(ValidationError):
            WhiteLabelConfig(org_id="org/id", company_name="Test")

    def test_valid_org_id_with_hyphens_underscores(self):
        config = WhiteLabelConfig(org_id="my-org_123", company_name="Test")
        assert config.org_id == "my-org_123"

    def test_invalid_color_format(self):
        with pytest.raises(ValidationError):
            WhiteLabelConfig(
                org_id="test",
                company_name="Test",
                primary_color="red",
            )

    def test_valid_hex_color(self):
        config = WhiteLabelConfig(
            org_id="test",
            company_name="Test",
            primary_color="#ABCDEF",
        )
        assert config.primary_color == "#ABCDEF"

    def test_domain_validation_valid(self):
        config = WhiteLabelConfig(
            org_id="test",
            company_name="Test",
            custom_domain="app.example.com",
        )
        assert config.custom_domain == "app.example.com"

    def test_domain_validation_invalid(self):
        with pytest.raises(ValidationError, match="Invalid domain"):
            WhiteLabelConfig(
                org_id="test",
                company_name="Test",
                custom_domain="not-a-domain",
            )

    def test_domain_lowercased(self):
        config = WhiteLabelConfig(
            org_id="test",
            company_name="Test",
            custom_domain="APP.Example.COM",
        )
        assert config.custom_domain == "app.example.com"

    def test_css_sanitization_javascript(self):
        with pytest.raises(ValidationError, match="dangerous"):
            WhiteLabelConfig(
                org_id="test",
                company_name="Test",
                custom_css="body { background: javascript:alert(1) }",
            )

    def test_css_sanitization_import(self):
        with pytest.raises(ValidationError, match="dangerous"):
            WhiteLabelConfig(
                org_id="test",
                company_name="Test",
                custom_css="@import url('evil.css');",
            )

    def test_css_sanitization_expression(self):
        with pytest.raises(ValidationError, match="dangerous"):
            WhiteLabelConfig(
                org_id="test",
                company_name="Test",
                custom_css="div { width: expression(alert(1)) }",
            )

    def test_css_sanitization_safe(self):
        config = WhiteLabelConfig(
            org_id="test",
            company_name="Test",
            custom_css="body { background: #000; color: #fff; }",
        )
        assert config.custom_css is not None
        assert "background" in config.custom_css

    def test_brand_themes(self):
        assert BrandTheme.DARK.value == "dark"
        assert BrandTheme.LIGHT.value == "light"
        assert BrandTheme.CUSTOM.value == "custom"


# --- WhiteLabelService Tests ---


class TestWhiteLabelService:
    @pytest.mark.asyncio
    async def test_save_and_get_config(self, service, sample_config):
        result = await service.save_config(sample_config)
        assert result["status"] == "saved"
        assert result["org_id"] == "acme-corp"

        retrieved = await service.get_config("acme-corp")
        assert retrieved is not None
        assert retrieved.company_name == "ACME Corporation"
        assert retrieved.primary_color == "#FF6B35"

    @pytest.mark.asyncio
    async def test_get_nonexistent_config(self, service):
        result = await service.get_config("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_config(self, service, sample_config):
        await service.save_config(sample_config)
        deleted = await service.delete_config("acme-corp")
        assert deleted is True

        result = await service.get_config("acme-corp")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, service):
        deleted = await service.delete_config("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_get_css_variables_with_config(self, service, sample_config):
        await service.save_config(sample_config)
        css_vars = await service.get_css_variables("acme-corp")
        assert css_vars["--gps-bg"] == "#1A1A2E"
        assert css_vars["--gps-accent"] == "#FF6B35"
        assert css_vars["--gps-green"] == "#004E89"
        assert css_vars["--gps-purple"] == "#FFD166"
        assert css_vars["--gps-font"] == "Roboto, sans-serif"

    @pytest.mark.asyncio
    async def test_get_css_variables_default(self, service):
        css_vars = await service.get_css_variables("nonexistent")
        assert css_vars == _default_css_vars()

    @pytest.mark.asyncio
    async def test_get_branding_with_config(self, service, sample_config):
        await service.save_config(sample_config)
        branding = await service.get_branding("acme-corp")
        assert branding["company_name"] == "ACME Corporation"
        assert branding["logo_url"] == "https://acme.com/logo.png"
        assert branding["hide_powered_by"] is True
        assert branding["theme"] == "dark"
        assert "--gps-bg" in branding["css_variables"]

    @pytest.mark.asyncio
    async def test_get_branding_default(self, service):
        branding = await service.get_branding("nonexistent")
        assert branding["company_name"] == "Git Phantom Scope"
        assert branding["hide_powered_by"] is False

    @pytest.mark.asyncio
    async def test_overwrite_config(self, service, sample_config):
        await service.save_config(sample_config)

        updated = WhiteLabelConfig(
            org_id="acme-corp",
            company_name="ACME Updated",
            primary_color="#000000",
        )
        await service.save_config(updated)

        config = await service.get_config("acme-corp")
        assert config is not None
        assert config.company_name == "ACME Updated"
        assert config.primary_color == "#000000"


# --- Default helpers ---


class TestDefaults:
    def test_default_css_vars(self):
        css = _default_css_vars()
        assert css["--gps-bg"] == "#0D1117"
        assert css["--gps-accent"] == "#58A6FF"
        assert len(css) == 8

    def test_default_branding(self):
        branding = _default_branding()
        assert branding["company_name"] == "Git Phantom Scope"
        assert branding["watermark_text"] == "Git Phantom Scope"
        assert branding["hide_powered_by"] is False
        assert "css_variables" in branding


# --- Error class ---


class TestWhiteLabelError:
    def test_default_message(self):
        err = WhiteLabelError()
        assert err.code == "WHITE_LABEL_ERROR"
        assert err.status_code == 400

    def test_custom_message(self):
        err = WhiteLabelError("Custom error message")
        assert err.message == "Custom error message"

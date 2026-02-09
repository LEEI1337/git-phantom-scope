"""Tests for Renderer (watermark, overlay) and Packager (ZIP bundle)."""

import io
import zipfile

import pytest
from PIL import Image

from services.packager import Packager, Renderer


def _create_test_image(width: int = 400, height: int = 200) -> bytes:
    """Create a simple test PNG image."""
    img = Image.new("RGBA", (width, height), (13, 17, 23, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


@pytest.fixture
def renderer():
    return Renderer()


@pytest.fixture
def packager():
    return Packager()


@pytest.fixture
def test_image():
    return _create_test_image()


class TestRenderer:
    def test_watermark_free_tier(self, renderer, test_image):
        result = renderer.add_watermark(test_image, tier="free")
        assert isinstance(result, bytes)
        assert len(result) > 0
        # Verify it's still a valid PNG
        img = Image.open(io.BytesIO(result))
        assert img.format == "PNG"

    def test_watermark_pro_tier(self, renderer, test_image):
        result = renderer.add_watermark(test_image, tier="pro")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_watermark_enterprise_no_watermark(self, renderer, test_image):
        result = renderer.add_watermark(test_image, tier="enterprise")
        # Enterprise returns original bytes unchanged
        assert result == test_image

    def test_watermark_preserves_image_dimensions(self, renderer, test_image):
        result = renderer.add_watermark(test_image, tier="free")
        original = Image.open(io.BytesIO(test_image))
        watermarked = Image.open(io.BytesIO(result))
        assert watermarked.size == original.size

    def test_watermark_invalid_image_returns_original(self, renderer):
        bad_data = b"not an image"
        result = renderer.add_watermark(bad_data, tier="free")
        assert result == bad_data

    def test_text_overlay_bottom(self, renderer, test_image):
        result = renderer.create_text_overlay(test_image, "Test Text", position="bottom")
        assert isinstance(result, bytes)
        img = Image.open(io.BytesIO(result))
        assert img.format == "PNG"

    def test_text_overlay_top(self, renderer, test_image):
        result = renderer.create_text_overlay(test_image, "Top Text", position="top")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_text_overlay_center(self, renderer, test_image):
        result = renderer.create_text_overlay(test_image, "Center", position="center")
        assert isinstance(result, bytes)

    def test_text_overlay_invalid_image_returns_original(self, renderer):
        bad_data = b"not an image"
        result = renderer.create_text_overlay(bad_data, "Text")
        assert result == bad_data

    def test_watermark_large_image(self, renderer):
        large_image = _create_test_image(1920, 1080)
        result = renderer.add_watermark(large_image, tier="free")
        img = Image.open(io.BytesIO(result))
        assert img.size == (1920, 1080)


class TestPackager:
    def test_create_bundle_readme_only(self, packager):
        bundle = packager.create_bundle(readme_content="# Hello World")
        assert isinstance(bundle, bytes)

        # Verify ZIP structure
        with zipfile.ZipFile(io.BytesIO(bundle)) as zf:
            names = zf.namelist()
            assert "README.md" in names
            assert "SETUP.md" in names
            content = zf.read("README.md").decode()
            assert "Hello World" in content

    def test_create_bundle_with_banner(self, packager, test_image):
        bundle = packager.create_bundle(
            readme_content="# Profile",
            banner_image=test_image,
        )

        with zipfile.ZipFile(io.BytesIO(bundle)) as zf:
            assert "profile-banner.png" in zf.namelist()
            img_data = zf.read("profile-banner.png")
            assert len(img_data) > 0

    def test_create_bundle_with_social_cards(self, packager, test_image):
        cards = {"github": test_image, "linkedin": test_image}
        bundle = packager.create_bundle(
            readme_content="# Profile",
            social_cards=cards,
        )

        with zipfile.ZipFile(io.BytesIO(bundle)) as zf:
            names = zf.namelist()
            assert "social-cards/github.png" in names
            assert "social-cards/linkedin.png" in names

    def test_create_bundle_with_cover_images(self, packager, test_image):
        covers = [test_image, test_image]
        bundle = packager.create_bundle(
            readme_content="# Profile",
            cover_images=covers,
        )

        with zipfile.ZipFile(io.BytesIO(bundle)) as zf:
            names = zf.namelist()
            assert "repo-covers/cover-1.png" in names
            assert "repo-covers/cover-2.png" in names

    def test_create_bundle_with_custom_instructions(self, packager):
        bundle = packager.create_bundle(
            readme_content="# Profile",
            instructions="# Custom Setup\nDo this.",
        )

        with zipfile.ZipFile(io.BytesIO(bundle)) as zf:
            content = zf.read("SETUP.md").decode()
            assert "Custom Setup" in content

    def test_create_bundle_default_instructions(self, packager):
        bundle = packager.create_bundle(readme_content="# Profile")

        with zipfile.ZipFile(io.BytesIO(bundle)) as zf:
            content = zf.read("SETUP.md").decode()
            assert "Git Phantom Scope" in content

    def test_create_full_bundle(self, packager, test_image):
        cards = {"github": test_image, "twitter": test_image}
        covers = [test_image]
        bundle = packager.create_bundle(
            readme_content="# Full Profile",
            banner_image=test_image,
            cover_images=covers,
            social_cards=cards,
            instructions="# Full Instructions",
        )

        with zipfile.ZipFile(io.BytesIO(bundle)) as zf:
            names = zf.namelist()
            assert len(names) == 6  # README + SETUP + banner + 2 social + 1 cover
            assert "README.md" in names
            assert "SETUP.md" in names
            assert "profile-banner.png" in names

    def test_bundle_is_valid_zip(self, packager, test_image):
        bundle = packager.create_bundle(
            readme_content="# Test",
            banner_image=test_image,
        )
        assert zipfile.is_zipfile(io.BytesIO(bundle))

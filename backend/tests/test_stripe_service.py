"""Tests for Stripe payment integration service."""

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.stripe_service import (
    TIER_PRODUCTS,
    PaymentError,
    StripeService,
    UserTier,
    get_tier_features,
)


@pytest.fixture
def stripe_service():
    """Create a StripeService with a fake API key."""
    return StripeService(api_key="sk_test_fake_key_for_testing")


@pytest.fixture
def disabled_service():
    """Create a StripeService with no API key (disabled)."""
    return StripeService(api_key=None)


class TestUserTier:
    def test_free_tier(self):
        assert UserTier.FREE.value == "free"

    def test_pro_tier(self):
        assert UserTier.PRO.value == "pro"

    def test_enterprise_tier(self):
        assert UserTier.ENTERPRISE.value == "enterprise"


class TestTierProducts:
    def test_pro_product_defined(self):
        assert UserTier.PRO in TIER_PRODUCTS

    def test_enterprise_product_defined(self):
        assert UserTier.ENTERPRISE in TIER_PRODUCTS

    def test_free_not_in_products(self):
        assert UserTier.FREE not in TIER_PRODUCTS

    def test_pro_has_pricing(self):
        pro = TIER_PRODUCTS[UserTier.PRO]
        assert pro["price_monthly_cents"] > 0
        assert pro["price_yearly_cents"] > 0

    def test_yearly_cheaper_than_monthly(self):
        """Yearly should be cheaper per month than monthly billing."""
        pro = TIER_PRODUCTS[UserTier.PRO]
        yearly_per_month = pro["price_yearly_cents"] / 12
        assert yearly_per_month < pro["price_monthly_cents"]


class TestStripeServiceInit:
    def test_enabled_with_key(self, stripe_service):
        assert stripe_service.is_enabled is True

    def test_disabled_without_key(self, disabled_service):
        assert disabled_service.is_enabled is False


class TestCheckoutSession:
    @pytest.mark.asyncio
    async def test_not_enabled_raises(self, disabled_service):
        with pytest.raises(PaymentError, match="not configured"):
            await disabled_service.create_checkout_session(
                tier=UserTier.PRO,
                session_id="sess-1",
            )

    @pytest.mark.asyncio
    async def test_free_tier_raises(self, stripe_service):
        with pytest.raises(PaymentError, match="Cannot purchase free tier"):
            await stripe_service.create_checkout_session(
                tier=UserTier.FREE,
                session_id="sess-1",
            )

    @pytest.mark.asyncio
    async def test_successful_checkout(self, stripe_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "url": "https://checkout.stripe.com/pay/cs_test_123",
            "id": "cs_test_123",
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await stripe_service.create_checkout_session(
                tier=UserTier.PRO,
                session_id="sess-test",
            )

        assert result["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_123"
        assert result["checkout_session_id"] == "cs_test_123"
        assert result["tier"] == "pro"
        assert result["billing_period"] == "monthly"

    @pytest.mark.asyncio
    async def test_checkout_yearly(self, stripe_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "url": "https://checkout.stripe.com/pay/cs_test_456",
            "id": "cs_test_456",
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await stripe_service.create_checkout_session(
                tier=UserTier.PRO,
                session_id="sess-test",
                billing_period="yearly",
            )

        assert result["billing_period"] == "yearly"
        assert result["amount_cents"] == TIER_PRODUCTS[UserTier.PRO]["price_yearly_cents"]

    @pytest.mark.asyncio
    async def test_checkout_stripe_error(self, stripe_service):
        mock_response = AsyncMock()
        mock_response.status_code = 400

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(PaymentError, match="creation failed"):
                await stripe_service.create_checkout_session(
                    tier=UserTier.PRO,
                    session_id="sess-1",
                )

    @pytest.mark.asyncio
    async def test_checkout_network_error(self, stripe_service):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.RequestError("timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(PaymentError, match="unavailable"):
                await stripe_service.create_checkout_session(
                    tier=UserTier.PRO,
                    session_id="sess-1",
                )


class TestPortalSession:
    @pytest.mark.asyncio
    async def test_portal_not_enabled(self, disabled_service):
        with pytest.raises(PaymentError, match="not configured"):
            await disabled_service.create_portal_session("cus_test_123")

    @pytest.mark.asyncio
    async def test_portal_success(self, stripe_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "url": "https://billing.stripe.com/p/session/test_portal",
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await stripe_service.create_portal_session("cus_test_123")

        assert "portal_url" in result
        assert "stripe.com" in result["portal_url"]


class TestWebhookVerification:
    def _sign_payload(self, payload: bytes, secret: str) -> str:
        """Helper to create a valid Stripe webhook signature."""
        timestamp = str(int(time.time()))
        signed_payload = f"{timestamp}.".encode() + payload
        sig = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        return f"t={timestamp},v1={sig}"

    @pytest.mark.asyncio
    async def test_valid_signature(self, stripe_service):
        payload = json.dumps(
            {
                "type": "checkout.session.completed",
                "data": {"object": {"metadata": {"gps_tier": "pro", "gps_session_id": "s-1"}}},
            }
        ).encode()
        secret = "whsec_test"  # noqa: S105
        signature = self._sign_payload(payload, secret)

        event = await stripe_service.verify_webhook_signature(payload, signature, secret)
        assert event["type"] == "checkout.session.completed"

    @pytest.mark.asyncio
    async def test_invalid_signature_raises(self, stripe_service):
        payload = b'{"type": "test"}'
        ts = str(int(time.time()))
        with pytest.raises(PaymentError, match="verification failed"):
            await stripe_service.verify_webhook_signature(
                payload, f"t={ts},v1=badsig", "whsec_test"
            )

    @pytest.mark.asyncio
    async def test_missing_signature_parts(self, stripe_service):
        with pytest.raises(PaymentError, match="format"):
            await stripe_service.verify_webhook_signature(
                b"payload", "invalid-header", "whsec_test"
            )

    @pytest.mark.asyncio
    async def test_expired_timestamp(self, stripe_service):
        old_ts = str(int(time.time()) - 600)  # 10 min ago
        payload = b'{"type": "test"}'
        signed = f"{old_ts}.".encode() + payload
        sig = hmac.new(b"whsec_test", signed, hashlib.sha256).hexdigest()
        header = f"t={old_ts},v1={sig}"

        with pytest.raises(PaymentError, match="too old"):
            await stripe_service.verify_webhook_signature(payload, header, "whsec_test")


class TestEventParsing:
    def test_get_tier_from_event(self, stripe_service):
        event = {
            "data": {"object": {"metadata": {"gps_tier": "pro", "gps_session_id": "s-1"}}},
        }
        assert stripe_service.get_tier_from_event(event) == UserTier.PRO

    def test_get_tier_invalid_value(self, stripe_service):
        event = {"data": {"object": {"metadata": {"gps_tier": "platinum"}}}}
        assert stripe_service.get_tier_from_event(event) is None

    def test_get_tier_missing_metadata(self, stripe_service):
        event = {"data": {"object": {}}}
        assert stripe_service.get_tier_from_event(event) is None

    def test_get_session_id(self, stripe_service):
        event = {
            "data": {"object": {"metadata": {"gps_session_id": "sess-abc"}}},
        }
        assert stripe_service.get_session_id_from_event(event) == "sess-abc"


class TestGetTierFeatures:
    def test_free_features(self):
        features = get_tier_features(UserTier.FREE)
        assert features["tier"] == "free"
        assert features["templates"] == 3
        assert features["watermark"] is True
        assert features["priority_queue"] is False

    def test_pro_features(self):
        features = get_tier_features(UserTier.PRO)
        assert features["tier"] == "pro"
        assert features["templates"] == 13
        assert features["watermark"] is False
        assert "stable_diffusion" in features["byok_providers"]
        assert "flux" in features["byok_providers"]

    def test_enterprise_features(self):
        features = get_tier_features(UserTier.ENTERPRISE)
        assert features["tier"] == "enterprise"
        assert features["api_access"] is True
        assert features["team_dashboard"] is True
        assert features["rate_limit_generate_per_day"] > features["templates"]

    def test_pro_has_more_generations_than_free(self):
        free = get_tier_features(UserTier.FREE)
        pro = get_tier_features(UserTier.PRO)
        assert pro["rate_limit_generate_per_day"] > free["rate_limit_generate_per_day"]

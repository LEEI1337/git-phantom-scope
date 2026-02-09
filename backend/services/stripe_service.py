"""Stripe Payment Integration — Tier management and billing.

Handles Pro/Enterprise tier upgrades via Stripe Checkout Sessions
and Customer Portal. Manages subscription lifecycle events through
webhooks with signature verification.

SECURITY:
- Stripe webhook signatures verified with constant-time comparison
- No PII stored in PostgreSQL — only anonymous tier metadata in Redis
- Stripe customer IDs are ephemeral session data (Redis, 30min TTL)
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import httpx

from app.config import get_settings
from app.exceptions import GPSBaseError
from app.logging_config import get_logger

logger = get_logger(__name__)


class UserTier(str, Enum):
    """User subscription tiers."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class PaymentError(GPSBaseError):
    """Payment processing error."""

    def __init__(self, message: str = "Payment processing failed") -> None:
        super().__init__(
            code="PAYMENT_ERROR",
            message=message,
            status_code=402,
        )


# Stripe product configuration
TIER_PRODUCTS = {
    UserTier.PRO: {
        "name": "Git Phantom Scope Pro",
        "description": "10+ premium templates, custom styles, priority generation",
        "price_monthly_cents": 999,  # $9.99/month
        "price_yearly_cents": 9999,  # $99.99/year
        "features": [
            "All 13 image templates",
            "5 README styles",
            "Custom color palettes",
            "Priority generation queue",
            "No watermark",
            "BYOK support (all providers)",
        ],
    },
    UserTier.ENTERPRISE: {
        "name": "Git Phantom Scope Enterprise",
        "description": "White-label, team analytics, API access, SLA",
        "price_monthly_cents": 4999,  # $49.99/month
        "price_yearly_cents": 49999,  # $499.99/year
        "features": [
            "Everything in Pro",
            "White-label configuration",
            "Team/org dashboard",
            "Dedicated API access",
            "Priority support & SLA",
            "Custom templates",
        ],
    },
}


class StripeService:
    """Stripe payment and subscription management.

    All Stripe API calls are async via httpx.
    Falls back gracefully when Stripe is not configured.
    """

    STRIPE_API_BASE = "https://api.stripe.com/v1"

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key
        if not self._api_key and hasattr(settings, "stripe_secret_key"):
            key = getattr(settings, "stripe_secret_key", None)
            if key:
                self._api_key = key.get_secret_value()
        self._enabled = bool(self._api_key)

    @property
    def is_enabled(self) -> bool:
        """Check if Stripe is configured."""
        return self._enabled

    def _headers(self) -> dict[str, str]:
        """Standard Stripe API headers."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    async def create_checkout_session(
        self,
        tier: UserTier,
        session_id: str,
        billing_period: str = "monthly",
        success_url: str = "http://localhost:3000/success",
        cancel_url: str = "http://localhost:3000/pricing",
    ) -> dict[str, Any]:
        """Create a Stripe Checkout Session for tier upgrade.

        Args:
            tier: Target subscription tier.
            session_id: GPS session ID for correlation.
            billing_period: 'monthly' or 'yearly'.
            success_url: Redirect URL on success.
            cancel_url: Redirect URL on cancel.

        Returns:
            Dict with checkout_url for client redirect.
        """
        if not self._enabled:
            raise PaymentError("Payment system not configured")

        if tier == UserTier.FREE:
            raise PaymentError("Cannot purchase free tier")

        product = TIER_PRODUCTS.get(tier)
        if not product:
            raise PaymentError("Invalid tier")

        price_cents = (
            product["price_monthly_cents"]
            if billing_period == "monthly"
            else product["price_yearly_cents"]
        )

        form_data = {
            "mode": "subscription",
            "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": cancel_url,
            "line_items[0][price_data][currency]": "usd",
            "line_items[0][price_data][unit_amount]": str(price_cents),
            "line_items[0][price_data][recurring][interval]": (
                "month" if billing_period == "monthly" else "year"
            ),
            "line_items[0][price_data][product_data][name]": product["name"],
            "line_items[0][price_data][product_data][description]": product["description"],
            "line_items[0][quantity]": "1",
            "metadata[gps_session_id]": session_id,
            "metadata[gps_tier]": tier.value,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.STRIPE_API_BASE}/checkout/sessions",
                    headers=self._headers(),
                    data=form_data,
                )

            if response.status_code != 200:
                logger.warning(
                    "stripe_checkout_failed",
                    status=response.status_code,
                )
                raise PaymentError("Checkout session creation failed")

            data = response.json()
            return {
                "checkout_url": data["url"],
                "checkout_session_id": data["id"],
                "tier": tier.value,
                "amount_cents": price_cents,
                "billing_period": billing_period,
            }

        except httpx.RequestError:
            raise PaymentError("Payment service unavailable")

    async def create_portal_session(
        self,
        stripe_customer_id: str,
        return_url: str = "http://localhost:3000/settings",
    ) -> dict[str, str]:
        """Create a Stripe Customer Portal session for subscription management.

        Args:
            stripe_customer_id: Stripe customer ID.
            return_url: URL to redirect after portal.

        Returns:
            Dict with portal_url.
        """
        if not self._enabled:
            raise PaymentError("Payment system not configured")

        form_data = {
            "customer": stripe_customer_id,
            "return_url": return_url,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.STRIPE_API_BASE}/billing_portal/sessions",
                    headers=self._headers(),
                    data=form_data,
                )

            if response.status_code != 200:
                raise PaymentError("Portal session creation failed")

            data = response.json()
            return {"portal_url": data["url"]}

        except httpx.RequestError:
            raise PaymentError("Payment service unavailable")

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        webhook_secret: str,
    ) -> dict[str, Any]:
        """Verify and parse a Stripe webhook event.

        Uses HMAC-SHA256 constant-time signature verification.

        Args:
            payload: Raw request body bytes.
            signature: Stripe-Signature header value.
            webhook_secret: Webhook endpoint secret.

        Returns:
            Parsed webhook event dict.
        """
        import hashlib
        import hmac
        import time as time_mod

        # Parse Stripe signature header (t=timestamp,v1=signature)
        sig_parts: dict[str, str] = {}
        for part in signature.split(","):
            key, _, value = part.partition("=")
            sig_parts[key.strip()] = value.strip()

        timestamp = sig_parts.get("t", "")
        v1_sig = sig_parts.get("v1", "")

        if not timestamp or not v1_sig:
            raise PaymentError("Invalid webhook signature format")

        # Verify timestamp is within 5 minutes
        try:
            ts = int(timestamp)
        except ValueError:
            raise PaymentError("Invalid webhook timestamp")

        if abs(time_mod.time() - ts) > 300:
            raise PaymentError("Webhook timestamp too old")

        # Compute expected signature
        signed_payload = f"{timestamp}.".encode() + payload
        expected_sig = hmac.new(
            webhook_secret.encode(),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison
        if not hmac.compare_digest(expected_sig, v1_sig):
            raise PaymentError("Webhook signature verification failed")

        import json

        return json.loads(payload)

    def get_tier_from_event(self, event: dict[str, Any]) -> UserTier | None:
        """Extract GPS tier from a Stripe webhook event."""
        metadata = event.get("data", {}).get("object", {}).get("metadata", {})
        tier_str = metadata.get("gps_tier", "")
        try:
            return UserTier(tier_str)
        except ValueError:
            return None

    def get_session_id_from_event(self, event: dict[str, Any]) -> str | None:
        """Extract GPS session ID from a Stripe webhook event."""
        metadata = event.get("data", {}).get("object", {}).get("metadata", {})
        return metadata.get("gps_session_id")


def get_tier_features(tier: UserTier) -> dict[str, Any]:
    """Get features and limits for a subscription tier."""
    if tier == UserTier.FREE:
        return {
            "tier": "free",
            "templates": 3,
            "readme_styles": 2,
            "watermark": True,
            "custom_colors": False,
            "byok_providers": ["gemini"],
            "rate_limit_generate_per_day": 5,
            "priority_queue": False,
        }
    if tier == UserTier.PRO:
        return {
            "tier": "pro",
            "templates": 13,
            "readme_styles": 5,
            "watermark": False,
            "custom_colors": True,
            "byok_providers": ["gemini", "openai", "stable_diffusion", "flux"],
            "rate_limit_generate_per_day": 50,
            "priority_queue": True,
        }
    return {
        "tier": "enterprise",
        "templates": 13,
        "readme_styles": 5,
        "watermark": False,
        "custom_colors": True,
        "custom_templates": True,
        "byok_providers": ["gemini", "openai", "stable_diffusion", "flux"],
        "rate_limit_generate_per_day": 500,
        "priority_queue": True,
        "api_access": True,
        "team_dashboard": True,
    }

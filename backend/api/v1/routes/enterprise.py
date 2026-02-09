"""
Enterprise API routes — team dashboard, white-label, PDF reports.

All enterprise routes require JWT Bearer token authentication
and are gated behind the Enterprise tier.
"""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.dependencies import get_redis
from app.logging_config import get_logger
from services.pdf_report import generate_pdf_report
from services.stripe_service import UserTier, get_tier_features
from services.team_analytics import (
    AggregationPeriod,
    TeamAnalyticsService,
    TeamMemberSummary,
)
from services.whitelabel import WhiteLabelConfig, WhiteLabelService

logger = get_logger(__name__)
router = APIRouter()


# --- Auth dependency ---


class EnterpriseUser(BaseModel):
    """Authenticated enterprise user context."""

    org_id: str
    tier: UserTier = UserTier.ENTERPRISE
    email_hash: str = ""


async def require_enterprise(
    x_org_id: str = Header(..., description="Organization ID"),
    x_api_key: str = Header(..., description="Enterprise API key"),
) -> EnterpriseUser:
    """Validate enterprise API key and return user context.

    In production, this verifies JWT tokens / API keys against
    the Stripe subscription. For now, validates header presence.
    """
    if not x_org_id or not x_api_key:
        raise HTTPException(status_code=401, detail="Enterprise auth required")

    if len(x_api_key) < 16:
        raise HTTPException(status_code=401, detail="Invalid API key format")

    email_hash = hashlib.sha256(x_api_key.encode()).hexdigest()[:16]
    return EnterpriseUser(
        org_id=x_org_id,
        tier=UserTier.ENTERPRISE,
        email_hash=email_hash,
    )


# --- Team Dashboard ---


class AddMemberRequest(BaseModel):
    """Request to add a team member analysis."""

    member_hash: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="SHA-256 hash of username",
    )
    scores: dict[str, float] = Field(default_factory=dict)
    archetype: str = Field(default="code_explorer", max_length=64)
    ai_tools_detected: list[str] = Field(default_factory=list)
    top_languages: list[str] = Field(default_factory=list)


class TeamDashboardResponse(BaseModel):
    """Team dashboard API response."""

    data: dict[str, Any]
    meta: dict[str, Any]


@router.post("/team/members", response_model=TeamDashboardResponse)
async def add_team_member(
    request: AddMemberRequest,
    user: EnterpriseUser = Depends(require_enterprise),
    redis: Any = Depends(get_redis),
) -> TeamDashboardResponse:
    """Add a team member's anonymous analysis to the org dashboard."""
    service = TeamAnalyticsService(redis)
    summary = TeamMemberSummary(
        member_hash=request.member_hash,
        scores=request.scores,
        archetype=request.archetype,
        ai_tools_detected=request.ai_tools_detected,
        top_languages=request.top_languages,
    )
    result_hash = await service.add_member_analysis(user.org_id, summary)
    return TeamDashboardResponse(
        data={"member_hash": result_hash, "status": "added"},
        meta={"org_id": user.org_id},
    )


@router.get("/team/dashboard", response_model=TeamDashboardResponse)
async def get_team_dashboard(
    period: str = Query("30d", pattern=r"^(7d|30d|90d|1y)$"),
    user: EnterpriseUser = Depends(require_enterprise),
    redis: Any = Depends(get_redis),
) -> TeamDashboardResponse:
    """Get aggregated team analytics dashboard."""
    period_map = {
        "7d": AggregationPeriod.WEEK,
        "30d": AggregationPeriod.MONTH,
        "90d": AggregationPeriod.QUARTER,
        "1y": AggregationPeriod.YEAR,
    }
    service = TeamAnalyticsService(redis)
    dashboard = await service.get_dashboard(
        user.org_id, period_map.get(period, AggregationPeriod.MONTH)
    )
    return TeamDashboardResponse(
        data=dashboard.model_dump(mode="json"),
        meta={"org_id": user.org_id, "period": period},
    )


@router.get("/team/comparison", response_model=TeamDashboardResponse)
async def get_team_comparison(
    user: EnterpriseUser = Depends(require_enterprise),
    redis: Any = Depends(get_redis),
) -> TeamDashboardResponse:
    """Get anonymized member comparisons for radar charts."""
    service = TeamAnalyticsService(redis)
    comparison = await service.get_team_comparison(user.org_id)
    return TeamDashboardResponse(
        data={"members": comparison},
        meta={"org_id": user.org_id},
    )


@router.delete("/team/members/{member_hash}")
async def remove_team_member(
    member_hash: str,
    user: EnterpriseUser = Depends(require_enterprise),
    redis: Any = Depends(get_redis),
) -> TeamDashboardResponse:
    """Remove a team member's analysis from the dashboard."""
    service = TeamAnalyticsService(redis)
    removed = await service.remove_member(user.org_id, member_hash)
    return TeamDashboardResponse(
        data={"removed": removed, "member_hash": member_hash},
        meta={"org_id": user.org_id},
    )


# --- White-Label ---


@router.put("/whitelabel", response_model=TeamDashboardResponse)
async def save_whitelabel_config(
    config: WhiteLabelConfig,
    user: EnterpriseUser = Depends(require_enterprise),
    redis: Any = Depends(get_redis),
) -> TeamDashboardResponse:
    """Save or update white-label branding configuration."""
    if config.org_id != user.org_id:
        raise HTTPException(status_code=403, detail="Cannot modify other org's config")
    service = WhiteLabelService(redis)
    result = await service.save_config(config)
    return TeamDashboardResponse(
        data=result,
        meta={"org_id": user.org_id},
    )


@router.get("/whitelabel", response_model=TeamDashboardResponse)
async def get_whitelabel_config(
    user: EnterpriseUser = Depends(require_enterprise),
    redis: Any = Depends(get_redis),
) -> TeamDashboardResponse:
    """Get current white-label branding configuration."""
    service = WhiteLabelService(redis)
    config = await service.get_config(user.org_id)
    if config is None:
        return TeamDashboardResponse(
            data={"configured": False},
            meta={"org_id": user.org_id},
        )
    return TeamDashboardResponse(
        data={"configured": True, "config": config.model_dump(mode="json")},
        meta={"org_id": user.org_id},
    )


@router.get("/whitelabel/branding", response_model=TeamDashboardResponse)
async def get_branding(
    user: EnterpriseUser = Depends(require_enterprise),
    redis: Any = Depends(get_redis),
) -> TeamDashboardResponse:
    """Get branding data for frontend rendering."""
    service = WhiteLabelService(redis)
    branding = await service.get_branding(user.org_id)
    return TeamDashboardResponse(
        data=branding,
        meta={"org_id": user.org_id},
    )


@router.delete("/whitelabel")
async def delete_whitelabel_config(
    user: EnterpriseUser = Depends(require_enterprise),
    redis: Any = Depends(get_redis),
) -> TeamDashboardResponse:
    """Delete white-label configuration."""
    service = WhiteLabelService(redis)
    deleted = await service.delete_config(user.org_id)
    return TeamDashboardResponse(
        data={"deleted": deleted},
        meta={"org_id": user.org_id},
    )


# --- Tier Features ---


@router.get("/features", response_model=TeamDashboardResponse)
async def get_enterprise_features(
    user: EnterpriseUser = Depends(require_enterprise),
) -> TeamDashboardResponse:
    """Get features available for the current tier."""
    features = get_tier_features(user.tier)
    return TeamDashboardResponse(
        data=features,
        meta={"org_id": user.org_id, "tier": user.tier.value},
    )


# --- PDF Reports ---


class PDFReportRequest(BaseModel):
    """Request for PDF scorecard generation."""

    scores: dict[str, float] = Field(default_factory=dict)
    archetype: dict[str, str] = Field(default_factory=dict)
    ai_analysis: dict[str, Any] = Field(default_factory=dict)
    tech_profile: dict[str, Any] = Field(default_factory=dict)


@router.post("/report/pdf")
async def generate_report(
    request: PDFReportRequest,
    user: EnterpriseUser = Depends(require_enterprise),
    redis: Any = Depends(get_redis),
) -> Response:
    """Generate a premium PDF developer scorecard."""
    service = WhiteLabelService(redis)
    branding = await service.get_branding(user.org_id)

    pdf_bytes = generate_pdf_report(
        scores=request.scores,
        archetype=request.archetype,
        ai_analysis=request.ai_analysis,
        tech_profile=request.tech_profile,
        branding=branding,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=scorecard.pdf",
            "Content-Length": str(len(pdf_bytes)),
        },
    )


# --- SSO ---


class SSOInitRequest(BaseModel):
    """Request to initiate SSO flow."""

    org_id: str = Field(..., min_length=1, max_length=64)


class SSOCallbackRequest(BaseModel):
    """SSO callback data."""

    state: str = Field(..., min_length=1)
    assertion_data: dict[str, Any] = Field(default_factory=dict)


@router.post("/sso/initiate", response_model=TeamDashboardResponse)
async def initiate_sso(
    request: SSOInitRequest,
    redis: Any = Depends(get_redis),
) -> TeamDashboardResponse:
    """Initiate SSO login flow for an organization."""
    from services.sso_service import SSOService

    service = SSOService(redis)
    result = await service.initiate_sso(request.org_id)
    return TeamDashboardResponse(
        data=result,
        meta={"org_id": request.org_id},
    )


@router.post("/sso/callback", response_model=TeamDashboardResponse)
async def sso_callback(
    request: SSOCallbackRequest,
    redis: Any = Depends(get_redis),
) -> TeamDashboardResponse:
    """Handle SSO callback and create authenticated session."""
    from services.sso_service import SSOService

    service = SSOService(redis)
    session = await service.verify_callback(
        state=request.state,
        assertion_data=request.assertion_data,
    )
    return TeamDashboardResponse(
        data={
            "session_id": session.session_id,
            "org_id": session.org_id,
            "role": session.role,
            "authenticated_at": session.authenticated_at,
        },
        meta={"provider": session.provider.value},
    )


@router.get("/sso/session/{session_id}", response_model=TeamDashboardResponse)
async def validate_sso_session(
    session_id: str,
    redis: Any = Depends(get_redis),
) -> TeamDashboardResponse:
    """Validate an SSO session."""
    from services.sso_service import SSOService

    service = SSOService(redis)
    session = await service.validate_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return TeamDashboardResponse(
        data={
            "valid": True,
            "org_id": session.org_id,
            "role": session.role,
        },
        meta={"session_id": session_id},
    )


@router.delete("/sso/session/{session_id}")
async def revoke_sso_session(
    session_id: str,
    redis: Any = Depends(get_redis),
) -> TeamDashboardResponse:
    """Revoke an SSO session."""
    from services.sso_service import SSOService

    service = SSOService(redis)
    revoked = await service.revoke_session(session_id)
    return TeamDashboardResponse(
        data={"revoked": revoked},
        meta={"session_id": session_id},
    )

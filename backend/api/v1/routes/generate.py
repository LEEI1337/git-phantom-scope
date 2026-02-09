"""Profile package generation endpoint.

POST /api/v1/public/generate - Start profile package generation
GET  /api/v1/public/generate/{job_id} - Check generation status
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field

import redis.asyncio as aioredis
from api.deps import rate_limit_generate
from app.config import get_settings
from app.dependencies import get_redis
from app.exceptions import SessionNotFoundError
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


class GenerateRequest(BaseModel):
    """Package generation request."""

    session_id: str = Field(..., description="Session ID from /analyze")
    template_id: str = Field("portfolio_banner", max_length=50)
    model_preferences: dict | None = Field(
        None,
        description="Model preferences for generation",
        examples=[{
            "text_model": "gemini-pro",
            "image_model": "gemini-imagen",
        }],
    )
    assets: list[str] = Field(
        default=["readme", "banner"],
        description="Assets to generate",
    )


class GenerateResponse(BaseModel):
    """Generation job response."""

    job_id: str
    status: str
    estimated_time_seconds: int
    meta: dict


class JobStatusResponse(BaseModel):
    """Generation job status response."""

    job_id: str
    status: str
    progress: int = 0
    download_url: str | None = None
    expires_at: str | None = None
    assets: dict | None = None
    meta: dict


@router.post("/generate", response_model=GenerateResponse)
async def generate_profile_package(
    request: GenerateRequest,
    redis: aioredis.Redis = Depends(get_redis),
    _rate_limit: None = Depends(rate_limit_generate),
) -> GenerateResponse:
    """Start profile package generation.

    Creates a background job to generate the requested assets
    (README, banner, covers, social cards) and returns a job_id
    for polling the status.
    """
    settings = get_settings()

    # Verify session exists
    session_data = await redis.get(f"session:{request.session_id}")
    if not session_data:
        raise SessionNotFoundError()

    # Create generation job
    job_id = str(uuid.uuid4())
    job_data = {
        "job_id": job_id,
        "session_id": request.session_id,
        "template_id": request.template_id,
        "model_preferences": request.model_preferences or {},
        "assets": request.assets,
        "status": "queued",
        "progress": 0,
    }

    # Store job in Redis
    await redis.setex(
        f"job:{job_id}",
        settings.redis_asset_ttl,
        json.dumps(job_data),
    )

    # TODO: Queue Celery task for actual generation
    # For MVP, we'll process synchronously or return queued status

    logger.info("generation_job_created", job_id=job_id, assets=request.assets)

    # Estimate time based on requested assets
    time_per_asset = {"readme": 10, "banner": 30, "repo_covers": 45, "social_cards": 30}
    estimated_time = sum(time_per_asset.get(a, 15) for a in request.assets)

    return GenerateResponse(
        job_id=job_id,
        status="queued",
        estimated_time_seconds=estimated_time,
        meta={"request_id": job_id},
    )


@router.get("/generate/{job_id}", response_model=JobStatusResponse)
async def get_generation_status(
    job_id: str = Path(..., description="Generation job ID"),
    redis: aioredis.Redis = Depends(get_redis),
) -> JobStatusResponse:
    """Check the status of a generation job."""
    job_data = await redis.get(f"job:{job_id}")
    if not job_data:
        raise SessionNotFoundError()

    job = json.loads(job_data)

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job.get("status", "unknown"),
        progress=job.get("progress", 0),
        download_url=job.get("download_url"),
        expires_at=job.get("expires_at"),
        assets=job.get("completed_assets"),
        meta={"request_id": job["job_id"]},
    )

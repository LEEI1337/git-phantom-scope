"""Celery worker for background generation jobs.

Handles async profile package generation including image creation,
watermarking, packaging, and temporary storage.

Docker Compose command: celery -A app.celery_worker worker --loglevel=info --concurrency=2
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from celery import Celery

from app.config import get_settings

settings = get_settings()

# Celery app instance
celery_app = Celery(
    "gps",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="generation",
    task_routes={
        "app.celery_worker.generate_profile_package": {"queue": "generation"},
    },
)


def _get_sync_redis():
    """Get a synchronous Redis client for Celery tasks."""
    import redis

    return redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


def _update_job_status(
    redis_client,
    job_id: str,
    status: str,
    progress: int = 0,
    download_url: str | None = None,
    completed_assets: dict | None = None,
    error: str | None = None,
) -> None:
    """Update job status in Redis."""
    job_key = f"job:{job_id}"
    job_data = redis_client.get(job_key)
    if not job_data:
        return

    job = json.loads(job_data)
    job["status"] = status
    job["progress"] = progress

    if download_url:
        job["download_url"] = download_url
        expires_at = datetime.now(UTC) + timedelta(seconds=settings.redis_asset_ttl)
        job["expires_at"] = expires_at.isoformat()

    if completed_assets:
        job["completed_assets"] = completed_assets

    if error:
        job["error"] = error

    redis_client.setex(job_key, settings.redis_asset_ttl, json.dumps(job))


@celery_app.task(
    bind=True,
    name="app.celery_worker.generate_profile_package",
    max_retries=2,
    default_retry_delay=30,
)
def generate_profile_package(self, job_id: str, session_id: str) -> dict:
    """Generate a profile package in the background.

    This task orchestrates the full generation pipeline:
    1. Retrieve scoring data from Redis session
    2. Generate requested assets (README, images)
    3. Apply watermarks
    4. Create ZIP bundle
    5. Store temporarily and update job status

    Args:
        job_id: Unique job identifier
        session_id: Redis session ID with scoring data

    Returns:
        Dict with job completion status
    """
    import asyncio

    redis_client = _get_sync_redis()

    try:
        _update_job_status(redis_client, job_id, "processing", progress=5)

        # Retrieve job data
        job_data = redis_client.get(f"job:{job_id}")
        if not job_data:
            return {"status": "failed", "error": "Job not found"}

        job = json.loads(job_data)

        # Retrieve session/scoring data
        session_data = redis_client.get(f"session:{session_id}")
        if not session_data:
            _update_job_status(redis_client, job_id, "failed", error="Session expired")
            return {"status": "failed", "error": "Session expired"}

        session = json.loads(session_data)
        scoring_result = session.get("scoring_result", {})
        requested_assets = job.get("assets", ["readme", "banner"])
        template_id = job.get("template_id", "portfolio_banner")

        _update_job_status(redis_client, job_id, "processing", progress=10)

        # Run async generation pipeline
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                _run_generation_pipeline(
                    job_id=job_id,
                    scoring_result=scoring_result,
                    requested_assets=requested_assets,
                    template_id=template_id,
                    model_preferences=job.get("model_preferences", {}),
                    redis_client=redis_client,
                )
            )
        finally:
            loop.close()

        # Update final status
        _update_job_status(
            redis_client,
            job_id,
            "completed",
            progress=100,
            download_url=result.get("download_url"),
            completed_assets=result.get("completed_assets"),
        )

        return {"status": "completed", "job_id": job_id}

    except Exception as exc:
        _update_job_status(redis_client, job_id, "failed", error="Generation failed")
        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"status": "failed", "job_id": job_id}
    finally:
        redis_client.close()


async def _run_generation_pipeline(
    job_id: str,
    scoring_result: dict,
    requested_assets: list[str],
    template_id: str,
    model_preferences: dict,
    redis_client,
) -> dict:
    """Execute the async generation pipeline.

    Delegates to ImageGenerator for the actual work.
    """
    from services.image_generator import ImageGenerator

    generator = ImageGenerator()
    return await generator.generate(
        job_id=job_id,
        scoring_result=scoring_result,
        requested_assets=requested_assets,
        template_id=template_id,
        model_preferences=model_preferences,
        progress_callback=lambda progress: _update_job_status(
            redis_client, job_id, "processing", progress=progress
        ),
    )

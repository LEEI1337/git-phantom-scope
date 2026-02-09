"""FastAPI Application Factory.

Creates and configures the FastAPI application with all middleware,
exception handlers, routes, and lifecycle events.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.config import get_settings
from app.exceptions import GPSBaseError
from app.logging_config import get_logger, setup_logging
from app.metrics import APP_INFO, HTTP_REQUEST_DURATION, HTTP_REQUESTS_TOTAL

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle: startup and shutdown."""
    settings = get_settings()

    # Startup
    setup_logging()
    APP_INFO.info(
        {
            "version": settings.app_version,
            "environment": settings.environment.value,
        }
    )
    logger.info(
        "application_starting",
        version=settings.app_version,
        environment=settings.environment.value,
    )

    # Initialize Redis connection pool
    from app.dependencies import close_redis, init_redis

    await init_redis()
    logger.info("redis_connected")

    # Initialize database
    from db.session import init_db

    await init_db()
    logger.info("database_connected")

    yield

    # Shutdown
    logger.info("application_shutting_down")
    await close_redis()
    from db.session import close_db

    await close_db()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Privacy-First GitHub Profile Intelligence & AI-Powered Visual Identity Platform"
        ),
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Prometheus metrics endpoint
    if settings.metrics_enabled:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)

    # Request middleware
    @app.middleware("http")
    async def request_middleware(request: Request, call_next) -> Response:
        """Add request ID, timing, and metrics to every request."""
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        # Bind request context for structured logging
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response: Response = await call_next(request)

        duration = time.perf_counter() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.4f}"

        # Metrics
        endpoint = request.url.path
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
        ).inc()
        HTTP_REQUEST_DURATION.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        return response

    # Exception handlers
    @app.exception_handler(GPSBaseError)
    async def gps_error_handler(_request: Request, exc: GPSBaseError) -> JSONResponse:
        """Handle all GPS custom exceptions."""
        logger.warning(
            "gps_error",
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions without leaking internals."""
        logger.exception("unhandled_error", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                }
            },
        )

    # Register routes
    from api.v1.router import api_v1_router

    app.include_router(api_v1_router, prefix="/api/v1")

    # Health endpoint (no prefix)
    @app.get("/health", tags=["System"])
    async def health_check() -> dict:
        """Basic health check."""
        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment.value,
        }

    return app


# Application instance
app = create_app()

"""API v1 router aggregation.

Combines all v1 route modules into a single router.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.v1.routes.analyze import router as analyze_router
from api.v1.routes.generate import router as generate_router
from api.v1.routes.keys import router as keys_router
from api.v1.routes.insights import router as insights_router

api_v1_router = APIRouter()

api_v1_router.include_router(analyze_router, prefix="/public", tags=["Profile Analysis"])
api_v1_router.include_router(generate_router, prefix="/public", tags=["Generation"])
api_v1_router.include_router(keys_router, tags=["BYOK Keys"])
api_v1_router.include_router(insights_router, prefix="/public", tags=["Insights"])

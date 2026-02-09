---
name: "develop-api-endpoint"
description: "Develop new FastAPI endpoints following Git Phantom Scope conventions: Pydantic validation, rate limiting, async patterns, and standard response format."
mode: "agent"
---

# Develop API Endpoint

## Context
Create new FastAPI endpoints following the Git Phantom Scope API conventions. Every endpoint must follow the established patterns for consistency and security.

## Endpoint Template

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from app.config import get_settings
from api.deps import rate_limit, get_redis, get_request_id

router = APIRouter(prefix="/api/v1", tags=["feature-name"])


class FeatureRequest(BaseModel):
    """Request model with full validation."""
    param: str = Field(..., min_length=1, max_length=100, description="Parameter description")

    class Config:
        json_schema_extra = {
            "example": {"param": "example_value"}
        }


class FeatureResponse(BaseModel):
    """Standard response wrapper."""
    data: dict
    meta: dict


@router.post(
    "/public/feature",
    response_model=FeatureResponse,
    status_code=200,
    summary="Feature endpoint description",
    responses={
        400: {"description": "Invalid request"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def feature_endpoint(
    request: FeatureRequest,
    req: Request,
    redis=Depends(get_redis),
    request_id: str = Depends(get_request_id),
    _rate_limit=Depends(rate_limit(max_requests=10, window_seconds=60)),
):
    """Endpoint docstring for OpenAPI docs."""
    try:
        result = await feature_service.process(request.param)
        return FeatureResponse(
            data=result,
            meta={"request_id": request_id, "cache_hit": False},
        )
    except GPSBaseError as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
```

## Conventions Checklist
- [ ] Pydantic model for request body
- [ ] Pydantic model for response body
- [ ] Rate limiting dependency
- [ ] Request ID tracking
- [ ] Async handler function
- [ ] Try/except with GPSBaseError
- [ ] Standard response format: `{"data": ..., "meta": {...}}`
- [ ] OpenAPI responses documented
- [ ] Summary and docstring provided
- [ ] No PII in logs or errors

## Route Organization
```
backend/api/v1/routes/
  analyze.py      - POST /api/v1/public/analyze
  generate.py     - POST /api/v1/public/generate, GET /api/v1/public/generate/{job_id}
  insights.py     - GET /api/v1/public/insights
  keys.py         - POST /api/v1/keys/validate
  templates.py    - GET /api/v1/templates (list available templates)
  health.py       - GET /health, GET /ready
```

## Implementation Files
- `backend/api/v1/routes/` - Route modules
- `backend/api/deps.py` - Shared dependencies
- `backend/app/exceptions.py` - Error classes

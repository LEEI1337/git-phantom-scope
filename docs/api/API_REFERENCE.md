# Git Phantom Scope — API Reference

## Overview

Git Phantom Scope provides a RESTful API for GitHub profile analysis, AI-powered visual
identity generation, and enterprise team analytics.

- **Base URL**: `https://api.gitphantomscope.com/api/v1`
- **Auth**: Public endpoints require no authentication. Enterprise endpoints use `X-Org-ID` + `X-API-Key` headers.
- **Rate Limits**: IP-based sliding window (configurable).
- **Response Format**: `{"data": ..., "meta": {"request_id": "...", "cache_hit": bool}}`

---

## Public Endpoints

### POST /public/analyze

Analyze a GitHub profile and return developer scorecard.

**Request Body:**
```json
{
  "github_username": "octocat",
  "preferences": {
    "career_goal": "fullstack",
    "style": "modern",
    "colors": ["#58A6FF", "#238636"]
  },
  "byok": {
    "gemini_key": "encrypted-key-here"
  }
}
```

**Response (200):**
```json
{
  "session_id": "uuid",
  "profile": {
    "username": "octocat",
    "avatar_url": "https://...",
    "bio": "...",
    "stats": { "repos": 42, "followers": 1234, "contributions_last_year": 567 }
  },
  "scores": {
    "activity": 85.2,
    "collaboration": 72.1,
    "stack_diversity": 68.5,
    "ai_savviness": 45.3
  },
  "archetype": {
    "id": "full_stack_polyglot",
    "name": "Full-Stack Polyglot",
    "description": "...",
    "confidence": 0.82,
    "alternatives": ["backend_architect"]
  },
  "ai_analysis": {
    "overall_bucket": "moderate",
    "detected_tools": ["copilot", "cursor"],
    "confidence": "high",
    "burst_score": 35
  },
  "tech_profile": {
    "languages": [{"name": "Python", "percentage": 45.2}],
    "frameworks": ["FastAPI", "React"],
    "top_repos": [{"name": "repo", "language": "Python", "stars": 10, "description": "..."}]
  },
  "meta": { "request_id": "uuid", "cache_hit": false }
}
```

**Rate Limit**: 3 requests/day per IP (configurable).

---

### POST /public/generate

Generate visual identity assets (async via Celery).

**Request Body:**
```json
{
  "session_id": "uuid-from-analyze",
  "template_id": "portfolio_banner",
  "model_preferences": {
    "text_model": "gemini",
    "image_model": "gemini"
  },
  "assets": ["banner", "readme", "social_card"]
}
```

**Response (202):**
```json
{
  "job_id": "celery-task-id",
  "status": "queued",
  "estimated_time_seconds": 30
}
```

---

### GET /public/generate/{job_id}

Check generation job status.

**Response (200):**
```json
{
  "job_id": "...",
  "status": "completed",
  "download_url": "/api/v1/public/generate/{job_id}/download",
  "completed_at": "2026-02-09T12:00:00Z"
}
```

---

### GET /public/generate/{job_id}/download

Download the generated ZIP package.

**Response**: Binary ZIP file with `Content-Type: application/zip`.

---

### GET /public/insights

Get aggregated, anonymous AI trend data.

**Query Parameters:**
| Parameter | Type | Default | Options |
|-----------|------|---------|---------|
| `metric` | string | `ai_usage_by_language` | `ai_usage_by_language`, `archetype_distribution`, `model_popularity`, `generation_trends` |
| `period` | string | `30d` | `7d`, `30d`, `90d`, `1y` |

**Response (200):**
```json
{
  "metric": "ai_usage_by_language",
  "period": "30d",
  "data": [
    { "language": "Python", "buckets": {"heavy": 45, "moderate": 120}, "sample_size": 165 }
  ],
  "updated_at": "2026-02-09",
  "meta": { "cache_hit": false }
}
```

---

### POST /keys/validate

Validate a BYOK API key.

**Request Body:**
```json
{
  "provider": "gemini",
  "api_key": "user-api-key"
}
```

**Response (200):**
```json
{
  "valid": true,
  "tier": "pro",
  "rate_limits": { "requests_per_minute": 60, "requests_per_day": 1000 },
  "features": { "text_generation": true, "image_generation": true }
}
```

---

## Enterprise Endpoints

All enterprise endpoints require the following headers:
- `X-Org-ID`: Organization identifier
- `X-API-Key`: Enterprise API key (min 16 characters)

### POST /enterprise/team/members

Add a team member's anonymous analysis.

**Request Body:**
```json
{
  "member_hash": "sha256-hash-of-username",
  "scores": { "activity": 85, "collaboration": 72, "stack_diversity": 68, "ai_savviness": 45 },
  "archetype": "full_stack_polyglot",
  "ai_tools_detected": ["copilot", "cursor"],
  "top_languages": ["Python", "TypeScript"]
}
```

---

### GET /enterprise/team/dashboard

Get aggregated team analytics.

**Query**: `?period=30d` (7d, 30d, 90d, 1y)

**Response:**
```json
{
  "data": {
    "org_id": "acme",
    "team_size": 12,
    "aggregate_scores": { "activity": 78.5, "collaboration": 65.2 },
    "archetype_distribution": { "full_stack_polyglot": 4, "backend_architect": 3 },
    "ai_adoption_rate": 75.0,
    "top_languages": [{ "language": "Python", "count": 8 }],
    "ai_tools_usage": { "copilot": 6, "cursor": 3 }
  },
  "meta": { "org_id": "acme", "period": "30d" }
}
```

---

### GET /enterprise/team/comparison

Get anonymized member score comparisons for radar charts.

---

### DELETE /enterprise/team/members/{member_hash}

Remove a team member's analysis.

---

### PUT /enterprise/whitelabel

Save white-label branding configuration.

**Request Body:**
```json
{
  "org_id": "acme",
  "company_name": "ACME Corp",
  "logo_url": "https://...",
  "theme": "dark",
  "primary_color": "#FF6B35",
  "secondary_color": "#004E89",
  "accent_color": "#FFD166",
  "hide_powered_by": true,
  "watermark_text": "ACME Analytics"
}
```

---

### GET /enterprise/whitelabel

Get current white-label configuration.

### GET /enterprise/whitelabel/branding

Get branding data for frontend rendering (CSS variables, logos, etc.).

### DELETE /enterprise/whitelabel

Delete white-label configuration.

---

### POST /enterprise/report/pdf

Generate a premium PDF developer scorecard.

**Request Body:**
```json
{
  "scores": { "activity": 85, "collaboration": 72 },
  "archetype": { "name": "Full-Stack Polyglot", "description": "..." },
  "ai_analysis": { "overall_bucket": "moderate", "detected_tools": ["copilot"] },
  "tech_profile": { "languages": [{"name": "Python", "percentage": 45}] }
}
```

**Response**: Binary PDF file (`application/pdf`).

---

### GET /enterprise/features

Get features available for the current tier.

---

### POST /enterprise/sso/initiate

Initiate SSO login flow.

**Request Body:**
```json
{ "org_id": "acme" }
```

**Response:**
```json
{
  "data": {
    "redirect_url": "https://idp.example.com/saml?...",
    "state": "random-state-token",
    "provider": "saml"
  }
}
```

---

### POST /enterprise/sso/callback

Handle SSO callback.

### GET /enterprise/sso/session/{session_id}

Validate an SSO session.

### DELETE /enterprise/sso/session/{session_id}

Revoke an SSO session.

---

## Health Check

### GET /health

**Response (200):**
```json
{
  "status": "healthy",
  "environment": "production",
  "version": "2.0.0"
}
```

---

## Error Format

All errors follow a consistent format:
```json
{
  "error": {
    "code": "GITHUB_USER_NOT_FOUND",
    "message": "GitHub user not found"
  }
}
```

### Common Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `GITHUB_USER_NOT_FOUND` | 404 | GitHub username does not exist |
| `GITHUB_RATE_LIMIT` | 429 | GitHub API rate limit exceeded |
| `RATE_LIMIT_EXCEEDED` | 429 | Application rate limit exceeded |
| `SESSION_NOT_FOUND` | 404 | Session expired or invalid |
| `BYOK_CRYPTO_ERROR` | 401 | Invalid or corrupted BYOK key |
| `GENERATION_ERROR` | 500 | Image generation failed |
| `MODEL_PROVIDER_ERROR` | 502 | AI model provider unavailable |
| `PAYMENT_ERROR` | 402 | Payment or subscription issue |
| `SSO_ERROR` | 401 | SSO authentication failed |
| `WHITE_LABEL_ERROR` | 400 | White-label configuration error |
| `REPORT_ERROR` | 500 | PDF report generation failed |
| `VALIDATION_ERROR` | 422 | Request validation failed |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/public/analyze` | 3/day | Per IP |
| `/public/generate` | 5/day | Per IP |
| All API endpoints | 30/min | Per IP |
| Enterprise endpoints | 60/min | Per org |

---

## BYOK (Bring Your Own Key)

Users can supply their own API keys for AI providers:

1. Frontend encrypts key with AES-256-GCM using WebCrypto API
2. Encrypted key sent via `X-Encrypted-Key` header
3. Backend decrypts in-memory for request duration only
4. Key never touches disk, database, or logs

**Supported Providers**: Gemini, OpenAI, Stable Diffusion, FLUX.1

---

## Tiers

| Feature | Free | Pro ($9.99/mo) | Enterprise ($49.99/mo) |
|---------|------|----------------|------------------------|
| Analyses/day | 3 | 50 | 500 |
| Image templates | 3 | 13 | 13 + custom |
| README styles | 2 | 5 | 5 + custom |
| Watermark | Yes | No | No |
| BYOK providers | Gemini | All 4 | All 4 |
| Team dashboard | No | No | Yes |
| White-label | No | No | Yes |
| PDF reports | No | No | Yes |
| SSO/SAML | No | No | Yes |
| API access | No | No | Yes |

---

*Last updated: 2026-02-09 | Git Phantom Scope V2.0*

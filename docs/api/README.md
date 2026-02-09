# Git Phantom Scope - API Reference

## Base URL

```
Development: http://localhost:8000/api/v1
Production:  https://api.gitphantomscope.com/api/v1
```

## Authentication

Public endpoints require no authentication.  
Pro/Enterprise endpoints require a JWT Bearer token in the `Authorization` header.

BYOK keys are sent via `X-Encrypted-Key` header (AES-256 encrypted client-side).

## Response Format

All responses follow this structure:

```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid-v4",
    "cache_hit": false
  }
}
```

## Endpoints

### POST /api/v1/public/analyze

Analyze a GitHub profile and return scoring data.

**Request Body:**
```json
{
  "github_username": "octocat"
}
```

**Response (200):**
```json
{
  "data": {
    "scores": {
      "activity": 75,
      "collaboration": 60,
      "stack_diversity": 85,
      "ai_savviness": 40
    },
    "archetype": "Full-Stack Polyglot",
    "languages": {"Python": 45, "TypeScript": 30, "Go": 25},
    "profile_summary": { ... }
  }
}
```

### POST /api/v1/public/generate

Generate visual identity assets (README, infographic, social card).

**Request Body:**
```json
{
  "session_id": "uuid",
  "template": "professional",
  "output_format": "png",
  "options": {
    "include_readme": true,
    "include_infographic": true
  }
}
```

**Response (202):**
```json
{
  "data": {
    "job_id": "uuid",
    "status": "queued",
    "estimated_time_seconds": 30
  }
}
```

### GET /api/v1/public/generate/{job_id}

Check generation job status and retrieve results.

**Response (200):**
```json
{
  "data": {
    "job_id": "uuid",
    "status": "completed",
    "download_url": "/api/v1/public/download/uuid",
    "expires_at": "2025-08-17T18:00:00Z"
  }
}
```

### POST /api/v1/keys/validate

Validate a BYOK API key.

**Headers:** `X-Encrypted-Key: <aes-256-encrypted-key>`

**Response (200):**
```json
{
  "data": {
    "valid": true,
    "provider": "gemini",
    "model_access": ["gemini-2.0-flash", "gemini-2.5-pro"]
  }
}
```

### GET /api/v1/public/insights

Get aggregated platform insights (anonymous analytics).

**Query Parameters:**
- `days` (int, default: 30) - Number of days to look back

**Response (200):**
```json
{
  "data": {
    "total_generations": 1500,
    "top_archetypes": [
      {"archetype": "Full-Stack Polyglot", "count": 320},
      {"archetype": "AI-Driven Indie Hacker", "count": 280}
    ],
    "popular_templates": ["professional", "creative"],
    "avg_generation_time_ms": 4500
  }
}
```

## Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 400 | BAD_REQUEST | Invalid request parameters |
| 404 | GITHUB_USER_NOT_FOUND | GitHub user does not exist |
| 422 | VALIDATION_ERROR | Request body validation failed |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Server error |

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| /public/analyze | 10 req/min |
| /public/generate | 5 req/min |
| /keys/validate | 20 req/min |
| /public/insights | 30 req/min |

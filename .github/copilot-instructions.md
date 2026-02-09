---
applyTo: "**"
description: "Git Phantom Scope - Project-specific AI Agent Instructions (PhantomScope V1.0)"
lastUpdated: "2025-08-17"
version: "1.0.0"
projectSource: "git-phantom-scope"
baseAgent: "NeuralArchitect V2.6"
---

# Git Phantom Scope - AI Agent Instructions

You are operating as **PhantomScope Agent V1.0** - a specialized AI development agent for the Git Phantom Scope platform, built upon NeuralArchitect V2.6 enterprise standards.

## Project Identity

- **Name:** Git Phantom Scope
- **Purpose:** Privacy-First GitHub Profile Intelligence & AI-Powered Visual Identity Platform
- **Owner:** LEEI1337 (github.com/LEEI1337)
- **License:** BSL-1.1 (Business Source License)
- **Stack:** FastAPI (Python 3.12+) | Next.js 14+ (TypeScript) | PostgreSQL 16+ | Redis 7+

## Core Directives

### 1. PRIVACY ABOVE EVERYTHING
- **NEVER** persist personally identifiable information (PII)
- **NEVER** store GitHub usernames, emails, or profile data in PostgreSQL
- PostgreSQL is ONLY for anonymous, aggregated analytics
- All user data lives in Redis with TTL (max 30 minutes)
- Generated assets auto-delete after 4 hours
- BYOK keys must be AES-256 encrypted client-side before transmission

### 2. ARCHITECTURE RULES
```
Backend:  FastAPI (Python 3.12+) with Pydantic v2
Frontend: Next.js 14+ with App Router, TypeScript strict mode
Database: PostgreSQL 16+ (analytics ONLY) + Redis 7+ (sessions/cache)
Queue:    Celery + Redis as broker
AI/ML:    Multi-model via BYOK (Gemini, OpenAI, SD, FLUX.1)
MLOps:    MLflow for prompt versioning
Monitor:  Prometheus + Grafana
```

### 3. FILE STRUCTURE COMPLIANCE
```
backend/app/         - FastAPI application core (main.py, config.py)
backend/api/v1/      - Versioned API routes
backend/db/          - Async SQLAlchemy (analytics models only)
backend/services/    - Business logic (github, scoring, rendering, etc.)
backend/skills/      - Skill system (base.py, registry.py, templates/)
backend/gateway/     - Session management, health monitoring
frontend/app/        - Next.js App Router pages
frontend/components/ - React components
frontend/lib/        - API client, utilities
docs/                - Documentation (API, architecture, guides)
infra/               - Docker, K8s configs
```

### 4. CODE STANDARDS

#### Python (Backend)
```python
# REQUIRED: Type hints on ALL functions
async def analyze_profile(username: str, session_id: str) -> ProfileAnalysis:
    """Analyze a GitHub profile and return scoring data."""
    ...

# REQUIRED: Pydantic models for ALL API I/O
class AnalyzeRequest(BaseModel):
    github_username: str = Field(..., min_length=1, max_length=39, pattern=r'^[a-zA-Z0-9-]+$')

# REQUIRED: Async patterns for I/O operations
async with httpx.AsyncClient() as client:
    response = await client.get(f"https://api.github.com/users/{username}")

# FORBIDDEN: Synchronous database calls
# FORBIDDEN: Hardcoded API keys or secrets
# FORBIDDEN: Storing PII in PostgreSQL
```

#### TypeScript (Frontend)
```typescript
// REQUIRED: Strict TypeScript, no 'any' type
interface ProfileData {
  readonly scores: ReadonlyArray<DimensionScore>;
  readonly archetype: DeveloperArchetype;
}

// REQUIRED: Server Components by default, 'use client' only when needed
// REQUIRED: Proper error boundaries
// FORBIDDEN: Direct API calls from components (use lib/api/)
```

### 5. API DESIGN RULES
- All endpoints under `/api/v1/`
- Public endpoints under `/api/v1/public/` (no auth required)
- Pro/Enterprise endpoints require JWT Bearer token
- ALWAYS return proper HTTP status codes (200, 201, 400, 401, 403, 404, 422, 429, 500)
- Rate limiting on all public endpoints (Redis-backed)
- Request validation via Pydantic models
- Response format: `{"data": ..., "meta": {"request_id": "...", "cache_hit": bool}}`

### 6. BYOK (Bring Your Own Key) PROTOCOL
```
1. User enters API key in frontend
2. Frontend encrypts with AES-256 (WebCrypto API)
3. Encrypted key sent to backend in X-Encrypted-Key header
4. Backend decrypts in-memory only for the duration of the request
5. Key NEVER touches disk, database, or logs
6. Key NEVER appears in error messages or stack traces
```

### 7. SCORING ENGINE RULES
Four scoring dimensions (0-100 each):
- **Activity Score:** Commit frequency, streak, recency
- **Collaboration Score:** PRs, issues, reviews, forks
- **Stack Diversity:** Languages, frameworks, tools
- **AI-Savviness:** AI tool usage, co-author tags, AI commit patterns

Developer Archetypes: Based on score combination pattern matching
- "AI-Driven Indie Hacker" - High AI + High Activity + Low Collab
- "Open Source Maintainer" - High Collab + High Activity
- "Full-Stack Polyglot" - High Diversity + Medium Everything
- etc. (see scoring_engine.py for full mapping)

### 8. SKILLS SYSTEM
Skills inherit from `SkillBase` (see backend/skills/base.py):
```python
class MySkill(SkillBase):
    metadata = SkillMetadata(
        name="my-skill",
        version="1.0.0",
        description="What this skill does",
        author="LEEI1337"
    )

    async def execute(self, context: SkillContext) -> SkillResult:
        # Implementation here
        ...
```

### 9. TESTING REQUIREMENTS
- Unit tests: pytest + pytest-asyncio
- API tests: httpx.AsyncClient with TestClient
- Coverage target: >80% for services/, >90% for api/
- Integration tests: Docker Compose test profile
- No mocks in production code, ever

### 10. DOCKER CONVENTIONS
```yaml
# Service naming: gps-{service}
services:
  gps-backend:    # FastAPI
  gps-frontend:   # Next.js
  gps-postgres:   # PostgreSQL (analytics)
  gps-redis:      # Redis (cache/sessions)
  gps-celery:     # Celery worker
  gps-mlflow:     # MLflow tracking
  gps-prometheus: # Metrics
  gps-grafana:    # Dashboards
```

## Error Handling Protocol

```python
# ALL service functions must follow this pattern:
from app.exceptions import GPSBaseError, ExternalServiceError

async def call_github_api(username: str) -> dict:
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise GPSBaseError(
                code="GITHUB_USER_NOT_FOUND",
                message=f"GitHub user not found",  # NO username in error
                status_code=404
            )
        raise ExternalServiceError("GitHub API unavailable")
    except httpx.RequestError:
        raise ExternalServiceError("GitHub API connection failed")
```

## Pre-Commit Checklist (PhantomScope-specific)

- [ ] No PII in any database model or migration
- [ ] BYOK keys never logged, stored, or exposed in errors
- [ ] All new endpoints have rate limiting
- [ ] Pydantic models validate all inputs
- [ ] Async patterns used for all I/O
- [ ] Redis TTL set on all cached data
- [ ] Tests cover happy path + error cases
- [ ] No hardcoded API keys or secrets
- [ ] Docker service names use `gps-` prefix
- [ ] API responses follow standard format

## Phantom Ecosystem Context

This project is part of the Phantom ecosystem:
- **phantom-neural-cortex** - AI development gateway (skills, sessions, MCP)
- **git-phantom-scope** - THIS PROJECT (GitHub intelligence + visual identity)

Code reuse from ecosystem:
- Skills system adapted from phantom-neural-cortex
- FastAPI patterns from zugangsweg-kompass
- Export/packaging from book-creator
- Microservice patterns from domain-prospector

## MCP Server Configuration

Active MCP servers for this project (see .mcp.json):
- sequential-thinking: Complex analysis planning
- memory: Cross-session knowledge retention
- filesystem: File operations within workspace
- github: GitHub API operations
- postgres: Database operations
- gemini: AI model access
- brave-search: Web research

---
*PhantomScope Agent V1.0 - Privacy-First Development*
*Built on NeuralArchitect V2.6 Enterprise Standards*

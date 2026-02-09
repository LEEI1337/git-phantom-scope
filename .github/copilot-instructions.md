---
applyTo: "**"
description: "Git Phantom Scope - Privacy-First GitHub Intelligence Platform Agent Instructions"
lastUpdated: "2026-02-09"
version: "2.0.0"
projectSource: "git-phantom-scope"
---

# Git Phantom Scope - Agent Instructions

Privacy-first GitHub profile intelligence & AI-powered visual identity platform.
Repository: LEEI1337/git-phantom-scope | License: BSL-1.1 | Branch: main

## 1. Project Overview

Git Phantom Scope analyzes public GitHub profiles to produce developer scorecards and AI-generated visual identity assets. It scores profiles across four dimensions (Activity, Collaboration, Stack Diversity, AI-Savviness), classifies developers into one of 10 archetypes, and generates downloadable visual assets. All analysis is ephemeral — no PII is ever persisted.

**Current State (Phase 3 complete, 116 tests passing, 99% scoring coverage):**
- Phases 1-3 shipped: Foundation, GitHub Integration, Scoring Engine V2
- Phase 4 next: Image Generation (Gemini Imagen, templates, watermark, packaging)

## 2. Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | FastAPI, Python 3.14, Pydantic v2 | Async-first, `GPS_` env prefix |
| Frontend | Next.js 14+, TypeScript strict, Tailwind | App Router, Server Components default |
| Database | PostgreSQL 16+ (asyncpg) | Analytics ONLY — zero PII |
| Cache | Redis 7+ | Sessions, profile cache, rate limits (TTL max 30min) |
| Queue | Celery + Redis broker | Async generation jobs |
| AI/ML | Gemini, OpenAI, SD, FLUX.1 via BYOK | Multi-model, user-supplied keys |
| MLOps | MLflow | Prompt versioning |
| Monitoring | Prometheus + Grafana | Metrics endpoint enabled |
| CI/CD | GitHub Actions (6 jobs) | Lint, type-check, test, security audit, build |
| Linting | ruff 0.8.6 | line-length=100, target py312 |

## 3. Security Rules (MANDATORY)

These rules are non-negotiable and override all other guidelines.

- **NEVER** persist PII (usernames, emails, profile data) in PostgreSQL
- **NEVER** include API keys, passwords, or secrets in code output
- **NEVER** expose internal details in error messages (no usernames, no stack traces to clients)
- **NEVER** use `exec`/`eval` on user input; use `subprocess` with `shell=False`
- PostgreSQL is ONLY for anonymous, aggregated analytics (`AIUsageBucket`, `TrendSnapshot`, `GenerationStat`)
- All user data lives in Redis with TTL (max 30 minutes)
- Generated assets auto-delete after 4 hours
- Use `SecretStr` for all sensitive config fields (see `app/config.py`)
- Use parameterized queries for ALL database access
- Use constant-time comparison for session IDs and tokens
- Validate ALL inputs with Pydantic models before processing
- Pin dependency versions; use `pip-audit` for vulnerability scanning

### BYOK Protocol
1. Frontend encrypts API key with AES-256 (WebCrypto API)
2. Encrypted key sent via `X-Encrypted-Key` header
3. Backend decrypts in-memory only for request duration
4. Key NEVER touches disk, database, or logs
5. Key NEVER appears in error messages or stack traces
6. If decryption fails, return generic 401 (no details)

## 4. Coding Standards

### Python (Backend)

```python
# Type hints on ALL functions — no exceptions
async def analyze_profile(username: str, session_id: str) -> ProfileAnalysis:
    """Analyze a GitHub profile and return scoring data."""
    ...

# Pydantic v2 models for ALL API I/O — use model_validate, model_dump
class AnalyzeRequest(BaseModel):
    github_username: str = Field(..., min_length=1, max_length=39, pattern=r'^[a-zA-Z0-9-]+$')

# Async patterns for ALL I/O operations
async with httpx.AsyncClient() as client:
    response = await client.get(f"https://api.github.com/users/{username}")

# Settings: use Environment enum + SecretStr
from app.config import Environment, Settings
from pydantic import SecretStr
settings = Settings(environment=Environment.TESTING, github_token=SecretStr("token"))

# Modern Python (3.12+): prefer int | str over Union[int, str]
# Use @override for method overrides
# Use from __future__ import annotations sparingly (deprecated in 3.14)
```

**FORBIDDEN:**
- Synchronous database calls
- Hardcoded API keys or secrets
- Storing PII in PostgreSQL
- `from __future__ import annotations` in new files (use PEP 649 deferred eval)
- `Any` type without justification

### TypeScript (Frontend)

```typescript
// Strict TypeScript — no 'any' type
interface ProfileData {
  readonly scores: ReadonlyArray<DimensionScore>;
  readonly archetype: DeveloperArchetype;
}

// Server Components by default — 'use client' only when interactivity is needed
// API calls go through lib/api/ — NEVER call backend directly from components
// Error boundaries required for all async pages
```

### Error Handling Pattern

```python
# ALL service functions follow this pattern:
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
                message="GitHub user not found",  # NO username in error
                status_code=404
            )
        raise ExternalServiceError("GitHub API unavailable")
    except httpx.RequestError:
        raise ExternalServiceError("GitHub API connection failed")
```

## 5. Project Structure

```
backend/
├── app/              # FastAPI core (main.py, config.py, dependencies.py, exceptions.py)
├── api/v1/routes/    # Versioned API routes (analyze.py, generate.py, health.py)
├── db/               # Async SQLAlchemy models + session (analytics ONLY)
├── services/         # Business logic:
│   ├── github_service.py      # GitHub API client (REST + GraphQL)
│   ├── scoring_engine.py      # V2: log scaling, time decay, Shannon entropy
│   ├── commit_analyzer.py     # V2: AI detection, burst analysis, tool patterns
│   ├── analytics_pipeline.py  # Anonymous analytics writer
│   ├── prompt_orchestrator.py # AI prompt management
│   └── image_generator.py     # (Phase 4) Gemini Imagen integration
├── skills/           # Skill system (base.py, registry.py, templates/)
├── gateway/          # Session management, health monitoring
└── tests/            # pytest + pytest-asyncio (116 tests, 99% scoring coverage)

frontend/
├── app/              # Next.js App Router pages
├── components/       # React components (ui/, features/)
└── lib/              # API client, utilities, types

docs/                 # API specs, architecture docs
infra/                # Docker, K8s configs, Prometheus
```

## 6. Scoring Engine V2 (Implemented)

### Four Dimensions (0-100 each)
| Dimension | Key Inputs | Algorithm |
|-----------|-----------|-----------|
| Activity | Commits, streak, recency, calendar data | `_log_scale()` + `_time_decay_weight()` |
| Collaboration | PRs, issues, reviews, forks, orgs | `_log_scale()` with org bonus |
| Stack Diversity | Languages, frameworks, tools, topics | Shannon entropy (`_entropy()`) |
| AI-Savviness | AI tools, co-author tags, commit patterns, config files | Commit analyzer + config detection |

### 10 Developer Archetypes
Weighted classification with `confidence` (0-1) and `alternatives` list:

| Archetype | Key Signal |
|-----------|-----------|
| `ai_indie_hacker` | High AI + High Activity + Low Collab |
| `open_source_maintainer` | High Collab + High Activity |
| `full_stack_polyglot` | High Diversity + Balanced scores |
| `backend_architect` | Backend ecosystem + High Activity |
| `frontend_craftsman` | Frontend ecosystem + High Activity |
| `devops_specialist` | DevOps ecosystem + High Activity |
| `data_scientist` | Data science ecosystem |
| `security_sentinel` | Security topics/tools detected |
| `rising_developer` | New account + High recent Activity |
| `code_explorer` | Fallback — moderate engagement |

### Commit Analyzer V2
- Detects: Copilot, Cursor, Windsurf, Aider, Claude, ChatGPT, Gemini, Tabnine, Codeium
- `burst_score` (0-100): Measures suspiciously fast commit sequences
- AI config file detection: `.github/copilot-instructions.md`, `.cursorrules`, `.windsurfrules`, `CLAUDE.md`, `AGENTS.md`

## 7. API Design

- All endpoints: `/api/v1/`
- Public (no auth): `/api/v1/public/` (analyze, health)
- Pro/Enterprise: JWT Bearer token required
- Response format: `{"data": ..., "meta": {"request_id": "...", "cache_hit": bool}}`
- Rate limiting: Redis-backed, per-IP, configurable via `Settings`
- HTTP codes: 200, 201, 400, 401, 403, 404, 422, 429, 500

## 8. Testing & Build Commands

```bash
# Bootstrap
cd backend && pip install -r requirements.txt
cd frontend && npm install

# Run tests (116 tests, all passing)
cd backend && python -m pytest tests/ -v --tb=short

# Lint & format
cd backend && ruff check . && ruff format .
cd frontend && npm run lint && npm run type-check

# Docker
docker compose up -d

# Security audit
cd backend && pip-audit -r requirements.txt
```

**Testing rules:**
- pytest + pytest-asyncio for all backend tests
- httpx.AsyncClient for API integration tests
- fakeredis for Redis mocking (use `await redis.close()`, NOT `aclose()`)
- Coverage target: >90% for services/, >80% overall
- No mocks in production code
- Use `Environment.TESTING` enum + `SecretStr()` wrappers in test fixtures

## 9. Docker Conventions

```yaml
# Service naming: gps-{service}
services:
  gps-backend:    # FastAPI (port 8000)
  gps-frontend:   # Next.js (port 3000)
  gps-postgres:   # PostgreSQL (analytics only)
  gps-redis:      # Redis (cache/sessions)
  gps-celery:     # Celery worker
  gps-mlflow:     # MLflow tracking
  gps-prometheus: # Metrics
  gps-grafana:    # Dashboards
```

## 10. Pre-Commit Checklist

- [ ] No PII in any database model or migration
- [ ] BYOK keys never logged, stored, or exposed in errors
- [ ] All new endpoints have rate limiting
- [ ] Pydantic models validate all inputs with `Field(...)` constraints
- [ ] Async patterns used for all I/O
- [ ] Redis TTL set on all cached data (max 30 min user data, 4h assets)
- [ ] Tests cover happy path + error cases
- [ ] No hardcoded API keys or secrets
- [ ] Docker service names use `gps-` prefix
- [ ] API responses follow `{"data": ..., "meta": {...}}` format
- [ ] `ruff check .` and `ruff format .` pass clean

## Resources

**MCP Servers** (see `.mcp.json`):
sequential-thinking, memory, filesystem, github, postgres, gemini, brave-search

**Ecosystem:**
- phantom-neural-cortex — AI gateway (skills, sessions)
- git-phantom-scope — THIS PROJECT

**Key Files:**
- `backend/app/config.py` — Settings with `GPS_` prefix, `Environment` enum, `SecretStr`
- `backend/services/scoring_engine.py` — V2 scoring (793 lines)
- `backend/services/commit_analyzer.py` — V2 AI detection (306 lines)
- `backend/services/analytics_pipeline.py` — Anonymous analytics writer
- `backend/app/exceptions.py` — `GPSBaseError`, `ExternalServiceError`, `GitHubUserNotFoundError`

---
Git Phantom Scope V2.0 — Privacy-First Development

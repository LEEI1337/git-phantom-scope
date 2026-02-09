# Git Phantom Scope - Architecture Overview

## System Architecture

```
+------------------+     +------------------+     +------------------+
|    Next.js 14+   |---->|   FastAPI 0.100+  |---->|  PostgreSQL 16+  |
|    (Frontend)    |     |    (Backend)      |     | (Analytics ONLY) |
+------------------+     +------------------+     +------------------+
                               |    |
                    +----------+    +----------+
                    v                          v
            +------------------+     +------------------+
            |    Redis 7+      |     |   Celery Worker   |
            | (Cache/Sessions) |     | (Async Generation)|
            +------------------+     +------------------+
                                           |
                              +------------+------------+
                              v            v            v
                         +---------+  +---------+  +---------+
                         | Gemini  |  | OpenAI  |  |SD/FLUX  |
                         |  API    |  |  API    |  |  API    |
                         +---------+  +---------+  +---------+
```

## Privacy Architecture

**Zero-PII Design:**
- PostgreSQL stores ONLY anonymous, aggregated analytics
- User data lives in Redis with 30-minute TTL
- Generated assets auto-delete after 4 hours
- BYOK keys: AES-256 client-side encryption, in-memory only on backend

```
User Browser                  Backend                   Storage
+-----------+    encrypted    +------------+    anonymous   +----------+
| AES-256   |--------------->| In-Memory   |-------------->| PostgreSQL|
| BYOK Key  |    key only    | Decryption  |    stats only | Analytics |
+-----------+                +------------+                +----------+
     |                            |
     |       profile data         v
     +---------------------->+----------+
                             |  Redis   |  TTL: 30 min
                             +----------+
```

## Scoring Engine

Four dimensions (0-100 each):

| Dimension | Signals | Weight |
|-----------|---------|--------|
| Activity | Commits, streak, recency, repo count | 25% |
| Collaboration | PRs, issues, reviews, forks | 25% |
| Stack Diversity | Languages, frameworks, tool breadth | 25% |
| AI-Savviness | AI tool usage, co-author tags, patterns | 25% |

## Component Map

| Component | Path | Purpose |
|-----------|------|---------|
| API Routes | `backend/api/v1/routes/` | HTTP endpoint handlers |
| Services | `backend/services/` | Business logic layer |
| Skills | `backend/skills/` | Pluggable skill system |
| Gateway | `backend/gateway/` | Session & health management |
| DB Models | `backend/db/models.py` | Analytics-only SQLAlchemy models |
| Frontend | `frontend/app/` | Next.js App Router pages |
| API Client | `frontend/lib/api.ts` | Typed HTTP client |

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend Framework | FastAPI | 0.100+ |
| Python Runtime | CPython | 3.12+ |
| Frontend Framework | Next.js | 14+ |
| Database | PostgreSQL | 16+ |
| Cache | Redis | 7+ |
| Task Queue | Celery | 5.3+ |
| ML Tracking | MLflow | 2.x |
| Monitoring | Prometheus + Grafana | Latest |
| Container | Docker Compose | v2 |

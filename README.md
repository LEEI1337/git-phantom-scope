<div align="center">

```
   ██████╗ ██╗████████╗    ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
  ██╔════╝ ██║╚══██╔══╝    ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
  ██║  ███╗██║   ██║       ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
  ██║   ██║██║   ██║       ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
  ╚██████╔╝██║   ██║       ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
   ╚═════╝ ╚═╝   ╚═╝       ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
                        ███████╗ ██████╗ ██████╗ ██████╗ ███████╗
                        ██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔════╝
                        ███████╗██║     ██║   ██║██████╔╝█████╗
                        ╚════██║██║     ██║   ██║██╔═══╝ ██╔══╝
                        ███████║╚██████╗╚██████╔╝██║     ███████╗
                        ╚══════╝ ╚═════╝ ╚═════╝ ╚═╝     ╚══════╝
```

**Privacy-First GitHub Profile Intelligence & AI-Powered Visual Identity Platform**

[![License: BSL-1.1](https://img.shields.io/badge/License-BSL--1.1-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14+-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

**Analyze any GitHub profile. Detect AI-assisted code. Generate stunning visual identities.**
**Zero data stored. Your keys, your models, your privacy.**

[Live Demo](https://leei1337.github.io/git-phantom-scope) |
[API Docs](docs/api/) |
[Architecture](docs/architecture/) |
[Roadmap](ROADMAP.md)

</div>

---

## What is Git Phantom Scope?

**Git Phantom Scope** transforms any public GitHub profile into a comprehensive visual identity package -- powered by AI, driven by privacy.

Enter a GitHub username, and the platform will:

1. **Analyze** the complete public profile (repos, languages, commits, contributions)
2. **Detect** AI-assisted code patterns (Copilot co-author tags, commit message analysis)
3. **Score** the developer across 4 dimensions (Activity, Collaboration, Stack Diversity, AI-Savviness)
4. **Classify** the developer archetype ("AI-Driven Indie Hacker", "DevOps Expert", etc.)
5. **Generate** personalized infographics, banners, README templates, and social cards
6. **Package** everything into a downloadable ZIP bundle

All of this happens **without storing any personal data**. Ever.

---

## Key Features

<table>
<tr>
<td width="33%" valign="top">

### Zero Data Storage
No accounts needed. No personal data persisted. Session cache expires in 30 minutes. Generated assets auto-delete after 4 hours. GDPR-compliant by design.

</td>
<td width="33%" valign="top">

### BYOK - Bring Your Own Key
Use your own API keys for Gemini, OpenAI, Anthropic, or Stable Diffusion. Keys are encrypted client-side (AES-256) and never touch disk. Works completely free with Gemini Free API.

</td>
<td width="33%" valign="top">

### AI Code Detection
Proprietary heuristics analyze commit messages, co-author tags, and code patterns to estimate AI-assisted code percentage. Visualized per-language and per-repository.

</td>
</tr>
<tr>
<td width="33%" valign="top">

### Multi-Model Generation
Choose your AI model for each task. Gemini for free users, DALL-E 3 for quality, Stable Diffusion for speed, FLUX.1 for artistic styles. Mix and match text + image models.

</td>
<td width="33%" valign="top">

### Profile Package Bundle
Get a complete visual identity: profile README.md, banner image, repository cover images, LinkedIn/Twitter social cards. All in one downloadable ZIP.

</td>
<td width="33%" valign="top">

### Anonymous Trend Analytics
Aggregated, anonymized insights about AI usage in open-source development. Which tools, which languages, how much? Valuable data without compromising privacy.

</td>
</tr>
</table>

---

## Architecture

```
                                    +------------------+
                                    |   Next.js 14+    |
                                    |   Frontend SPA   |
                                    +--------+---------+
                                             |
                                    +--------v---------+
                                    |   FastAPI Gateway |
                                    |   Rate Limiting   |
                                    |   BYOK Manager    |
                                    +--------+---------+
                                             |
                    +------------------------+------------------------+
                    |                        |                        |
           +--------v-------+     +---------v--------+     +---------v--------+
           | GitHub Data    |     | Analytics &      |     | Prompt           |
           | Service        |     | Scoring Engine   |     | Orchestrator     |
           | (REST+GraphQL) |     | (AI Detection)   |     | (Context Eng.)   |
           +--------+-------+     +---------+--------+     +---------+--------+
                    |                        |                        |
                    v                        v                        v
           +----------------+     +------------------+     +------------------+
           | Redis Cache    |     | PostgreSQL       |     | Model Connectors |
           | (Sessions,     |     | (Anonymous       |     | (Gemini, OpenAI, |
           |  GitHub Data)  |     |  Analytics Only) |     |  SD, FLUX.1)     |
           +----------------+     +------------------+     +------------------+
                                                                     |
                                                           +---------v--------+
                                                           | Rendering &      |
                                                           | Packaging        |
                                                           | (ZIP + Watermark)|
                                                           +------------------+
```

> Full C4 architecture diagrams available in [docs/architecture/](docs/architecture/)

---

## Tech Stack

<table>
<tr><th>Layer</th><th>Technology</th><th>Why</th></tr>
<tr><td><b>Frontend</b></td><td>Next.js 14+, React 18+, TypeScript, Tailwind CSS</td><td>SSR for SEO, App Router, modern DX</td></tr>
<tr><td><b>Backend</b></td><td>FastAPI (Python 3.12+), Pydantic v2</td><td>Async-native, auto-docs, type-safe</td></tr>
<tr><td><b>Database</b></td><td>PostgreSQL 16+ (analytics only)</td><td>Reliable, JSON support, only anonymous data</td></tr>
<tr><td><b>Cache</b></td><td>Redis 7+</td><td>Session cache, rate limiting, GitHub data TTL</td></tr>
<tr><td><b>Queue</b></td><td>Celery + Redis (broker)</td><td>Async image generation jobs</td></tr>
<tr><td><b>AI/ML</b></td><td>Gemini API, OpenAI, Stable Diffusion, FLUX.1</td><td>Multi-model BYOK support</td></tr>
<tr><td><b>MLOps</b></td><td>MLflow</td><td>Prompt versioning, experiment tracking</td></tr>
<tr><td><b>Monitoring</b></td><td>Prometheus + Grafana</td><td>Metrics, dashboards, alerting</td></tr>
<tr><td><b>Deploy</b></td><td>Docker Compose (dev), Cloud Run/K8s (prod)</td><td>Portable, scalable</td></tr>
</table>

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 20+
- A Gemini API Key (free at [ai.google.dev](https://ai.google.dev))

### 1. Clone & Configure

```bash
git clone https://github.com/LEEI1337/git-phantom-scope.git
cd git-phantom-scope
cp .env.example .env
# Add your Gemini API key to .env
```

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Grafana | http://localhost:3001 |
| MLflow | http://localhost:5000 |

### 4. Generate Your First Profile

```bash
curl -X POST http://localhost:8000/api/v1/public/analyze \
  -H "Content-Type: application/json" \
  -d '{"github_username": "torvalds"}'
```

---

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/public/analyze` | Analyze a GitHub profile |
| `POST` | `/api/v1/public/generate` | Generate profile package |
| `GET` | `/api/v1/public/generate/{job_id}` | Check generation status |
| `POST` | `/api/v1/keys/validate` | Validate BYOK API key |
| `GET` | `/api/v1/public/insights` | Get aggregated AI trends |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Prometheus metrics |

> Full OpenAPI specification: [docs/api/openapi_spec.yaml](docs/api/openapi_spec.yaml)

---

## Business Model

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | 3 analyses/day, watermark, 2 templates, Gemini Free |
| **Pro** | 9-19 EUR/mo | 50 analyses/day, 10+ templates, custom styles, no watermark |
| **Enterprise** | Custom | White-label, team analytics, API access, premium trend reports |
| **Data** | B2B | Anonymized AI trend reports for VCs, research institutes |

---

## Privacy & Security

- **Zero PII Storage** - No usernames, emails, or code persisted
- **Session-Only Processing** - All user data lives in Redis (TTL: 30 min)
- **Client-Side Encryption** - BYOK keys encrypted with AES-256 before transmission
- **No Tracking** - No cookies, no fingerprinting, no analytics on users
- **GDPR by Design** - No data to delete because none is stored
- **Rate Limiting** - Redis-backed, per-IP and per-username limits
- **Bot Protection** - hCaptcha/Turnstile integration

---

## Project Structure

```
git-phantom-scope/
+-- .github/
|   +-- copilot-instructions.md     # AI Agent Instructions
|   +-- prompts/                     # Copilot Skills (10 skills)
|   +-- workflows/                   # CI/CD Pipelines
|   +-- ISSUE_TEMPLATE/
+-- backend/
|   +-- app/
|   |   +-- main.py                  # FastAPI Application Factory
|   |   +-- config.py                # Pydantic Settings
|   |   +-- logging_config.py        # Structlog Setup
|   |   +-- metrics.py               # Prometheus Metrics
|   +-- api/
|   |   +-- v1/                      # API v1 Routes
|   |   +-- deps.py                  # Dependencies (auth, rate-limit)
|   +-- db/
|   |   +-- session.py               # Async SQLAlchemy
|   |   +-- models.py                # Analytics Models
|   |   +-- migrations/              # Alembic Migrations
|   +-- services/
|   |   +-- github_service.py        # GitHub REST + GraphQL
|   |   +-- scoring_engine.py        # Analytics & AI Detection
|   |   +-- prompt_orchestrator.py   # Context Engineering
|   |   +-- model_connector.py       # BYOK Multi-Provider
|   |   +-- renderer.py              # Image Rendering
|   |   +-- packager.py              # ZIP Bundling
|   +-- skills/
|   |   +-- base.py                  # Skill Base Class
|   |   +-- registry.py              # Skill Auto-Discovery
|   |   +-- templates/               # Infographic Templates
|   +-- gateway/
|       +-- session.py               # Session Management
|       +-- health.py                # Health Monitor
+-- frontend/
|   +-- app/                         # Next.js App Router
|   +-- components/                  # React Components
|   +-- lib/                         # API Client, Utils
|   +-- public/                      # Static Assets
+-- docs/
|   +-- api/                         # OpenAPI Spec
|   +-- architecture/                # PlantUML Diagrams
|   +-- guides/                      # Developer Guides
+-- infra/
|   +-- docker/                      # Dockerfiles
|   +-- k8s/                         # Kubernetes Manifests
+-- memory-bank/                     # Project Memory
+-- archive/                         # Reference Code from other repos
+-- site/                            # GitHub Pages Source
+-- README.md
+-- ROADMAP.md
+-- TODO.md
+-- docker-compose.yml
+-- LICENSE
```

---

## Development Roadmap

| Phase | Timeline | Status | Description |
|-------|----------|--------|-------------|
| **Phase 1** | Weeks 1-2 | Planned | Foundation: FastAPI skeleton, Docker, DB, Skills System |
| **Phase 2** | Weeks 3-4 | Planned | GitHub integration, scoring engine, AI detection |
| **Phase 3** | Weeks 5-8 | Planned | Prompt orchestrator, Gemini integration, rendering |
| **Phase 4** | Weeks 9-16 | Planned | BYOK system, pro tier, more templates |
| **Phase 5** | Weeks 17-24 | Planned | Payment integration, enterprise features |
| **Phase 6** | Weeks 25-36 | Planned | White-label, data products, trend API |

> Detailed roadmap: [ROADMAP.md](ROADMAP.md)

---

## Code Reuse

This project builds upon proven patterns from the Phantom ecosystem:

| Source Project | Reused Components |
|----------------|-------------------|
| [phantom-neural-cortex](https://github.com/LEEI1337/phantom-neural-cortex) | Skills system, session management, gateway, MCP config |
| zugangsweg-kompass | FastAPI factory, Pydantic config, async DB, rate limiting |
| book-creator | Export/download pattern, file cleanup, cover generation |
| Domain-Prospector | Microservice architecture, Docker Compose patterns |

---

## Contributing

We welcome contributions! Please read our [Contributing Guide](CONTRIBUTING.md) before submitting PRs.

**Important:** This project uses the Business Source License (BSL-1.1). Forking and redistribution require written permission from the maintainer. See [LICENSE](LICENSE) for details.

---

## License

**Business Source License 1.1 (BSL-1.1)**

- Source code is **viewable and auditable** by everyone
- **Contributions** via Pull Requests are welcome
- **Forking and redistribution** require written permission from [@LEEI1337](https://github.com/LEEI1337)
- After the Change Date (Feb 9, 2030), the license converts to Apache 2.0

See [LICENSE](LICENSE) for the full text.

---

<div align="center">

**Built by [@LEEI1337](https://github.com/LEEI1337)**

Part of the **Phantom Ecosystem**

[phantom-neural-cortex](https://github.com/LEEI1337/phantom-neural-cortex) | git-phantom-scope

---

*Analyze. Detect. Visualize. Privately.*

</div>

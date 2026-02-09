# GitProfileAI - Vollständige Projektspezifikation
Version 1.0 | Februar 2026

---

## TEIL 1: PROJEKT-ÜBERSICHT FÜR STAKEHOLDER

### 1.1 Vision & Mission

**Was bauen wir?**
Eine Enterprise-grade Plattform, die automatisch aus GitHub-Profilen personalisierte, visuell beeindruckende Infografiken und Profil-Pakete generiert – powered by verschiedenen KI-Bild-Modellen.

**Das Besondere:**
- **Zero Data Storage**: Wir speichern KEINE Userdaten, nur anonyme KI-Nutzungsstatistiken
- **BYOK (Bring Your Own Key)**: User bringen ihre eigenen API-Keys für KI-Modelle mit
- **Gemini Free Support**: Funktioniert auch komplett kostenlos mit Gemini Free API
- **AI-Code Detection**: Wir analysieren und visualisieren den KI-Anteil im Code
- **Personalisierte Pakete**: Jeder bekommt ein einzigartiges Bundle (README, Banner, Cover-Bilder)

**Goldgrube:**
Die aggregierten, anonymisierten Daten über KI-Nutzung in der Entwicklung sind extrem wertvoll:
- "Welche KI-Tools werden in welchen Sprachen wie stark genutzt?"
- "Wie entwickelt sich der KI-Anteil in Open-Source-Projekten?"
- Diese Insights verkaufen wir als Premium-Reports an Unternehmen, VCs, Research-Institute

### 1.2 Zielgruppen

1. **Developer (B2C)**
   - Portfolio-Visuals für LinkedIn, Bewerbungen
   - Coole GitHub-Profile-READMEs
   - Kostenlos mit Watermark

2. **Recruiter & HR**
   - Schneller Überblick über Kandidaten
   - Skill-Visualisierungen
   - AI-Savviness-Scores

3. **Unternehmen (B2B)**
   - Team-Dashboards
   - KI-Einsatz-Analytics
   - White-Label-Lösung
   - Zugriff auf aggregierte Trend-Daten (kostenpflichtig)

### 1.3 Geschäftsmodell

**Free Tier:**
- Komplett kostenlos
- Mit Watermark
- Gemini Free API (User bringt eigenen Key oder nutzt unseren mit Limits)
- 2-3 Basic-Templates
- Limitiert auf 3-5 Generierungen/Tag

**Pro Tier (9-19€/Monat):**
- Mehr Templates (10+)
- Ohne/mit kleinem Watermark
- Mehr Generierungen
- Tiefere Analytics
- Eigene Farben/Styles

**Enterprise/White-Label:**
- Custom Branding
- Eigene Domain
- Team-/Org-Analytics
- API-Zugriff
- Premium Trend-Reports

**Data Revenue:**
- Verkauf aggregierter KI-Trend-Reports
- API-Zugriff auf anonymisierte Statistiken
- Research-Partnerschaften

---

## TEIL 2: TECHNISCHE ARCHITEKTUR FÜR ENTWICKLER

### 2.1 System-Übersicht (High-Level)

```
┌─────────────────────────────────────────────────────────────┐
│                        USER FLOW                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. User gibt GitHub-Username ein                            │
│  2. Optional: Preferences (Farben, Stil, Career Goals)       │
│  3. Optional: BYOK (eigene API-Keys für Gemini/SD/etc.)     │
│  4. System analysiert GitHub-Profil                          │
│  5. System schätzt KI-Anteil im Code                         │
│  6. System generiert Infografiken mit gewählten Modellen     │
│  7. User lädt ZIP-Paket herunter (README, Banner, etc.)      │
│  8. Alle User-Daten werden sofort gelöscht                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     BACKEND SERVICES                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Frontend (Next.js) ──► API Gateway ──► Services:           │
│                              │                                │
│                              ├─► GitHub Data Service          │
│                              ├─► Analytics & Scoring Service  │
│                              ├─► Prompt Orchestrator          │
│                              ├─► Model Connectors (BYOK)      │
│                              ├─► Rendering Service            │
│                              └─► Analytics DB (anonym)        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Core-Komponenten

#### 2.2.1 Frontend (Next.js + React)

**Pages:**
- `/` - Landing Page mit Beispielen
- `/explore` - Public Explorer (Username-Eingabe)
- `/generate` - Generierungsflow
- `/insights` - Public KI-Trends Dashboard
- `/settings` - BYOK Key-Management (clientseitig verschlüsselt)

**State Management:**
- React Context für Session-State
- LocalStorage für BYOK-Keys (verschlüsselt)
- Keine Server-seitige User-Datenhaltung

**Key Features:**
- Real-time Visualisierungen (ECharts/Recharts)
- Drag & Drop für eigene Bilder/Logos
- Live-Preview der Infografiken

#### 2.2.2 API Gateway / BFF

**Tech Stack:**
- Node.js + NestJS oder FastAPI (Python)
- Redis für Session-Cache (TTL: 30 Min)
- Rate Limiting (Redis + express-rate-limit)

**Endpoints:**

```
POST   /api/v1/public/analyze
GET    /api/v1/public/profile/:username
POST   /api/v1/public/generate
GET    /api/v1/public/insights
POST   /api/v1/keys/validate (BYOK Key-Check)
GET    /api/v1/health
```

#### 2.2.3 GitHub Data Service

**Funktionen:**
- GitHub REST & GraphQL API Integration
- Rate-Limit-Management (5000 req/h Standard, 15000 für Enterprise)
- Caching (Redis, TTL 15-30 Min)
- Nur öffentliche Daten

**Gesammelte Daten (temporär):**
- User-Info (Name, Bio, Avatar-URL)
- Repositories (Name, Sprachen, Stars, Forks)
- Commits (Anzahl, Zeitserien)
- Pull Requests, Issues
- Contribution-Graph

**Output:**
Strukturiertes JSON ohne PII-Persistenz

#### 2.2.4 Analytics & Scoring Service

**AI-Code-Detection (Heuristiken):**
1. Commit-Message-Analyse:
   - Keywords: "copilot", "chatgpt", "gemini", "claude", "ai-generated"
   - Regex-Patterns
2. Co-Author-Detection:
   - GitHub Copilot Co-Author-Tags
3. Optional (Opt-in):
   - Git-Hook/Extension-Daten

**Scoring-Algorithmus:**
- Activity Score (0-100): Commits/Zeit, PR-Aktivität
- Collaboration Score: PRs zu fremden Repos, Reviews
- Stack Diversity: Anzahl Sprachen, Framework-Breite
- AI-Savviness: Geschätzter KI-Anteil + Tools

**Archetyp-Klassifikation:**
- "AI-Driven Indie Hacker"
- "Full-Stack Generalist"
- "DevOps Infrastructure Expert"
- "Data Science Specialist"
- etc.

**Output:**
```json
{
  "session_id": "uuid",
  "scores": {
    "activity": 85,
    "collaboration": 72,
    "stack_diversity": 68,
    "ai_savviness": 91
  },
  "archetype": "ai_indie_hacker",
  "tech_profile": {
    "languages": [
      {"name": "TypeScript", "percentage": 45},
      {"name": "Python", "percentage": 35}
    ],
    "frameworks": ["React", "FastAPI", "PyTorch"],
    "top_repos": [...]
  },
  "ai_analysis": {
    "overall_bucket": "30_60",
    "by_language": {
      "TypeScript": "30_60",
      "Python": "10_30"
    },
    "detected_tools": ["GitHub Copilot", "ChatGPT"]
  }
}
```

#### 2.2.5 Prompt Orchestrator (Context Engineering Layer)

**Basis:** Survey on Context Engineering for LLMs (2025)

**Pipeline:**
1. **Context Retrieval:**
   - Auswahl relevanter Profil-Teile
   - Top-3-Projekte, wichtigste Skills

2. **Context Processing:**
   - Kompression auf max. Token-Limits
   - Strukturierung für Modell-Typen

3. **Context Management:**
   - Template-System pro Modell
   - Trennung: System-Prompt + User-Context

**Templates:**

```
LLM (README-Generierung):
---
System: Du bist ein professioneller Tech-Writer...
User Context: 
- Archetype: {archetype}
- Scores: {scores}
- Top Skills: {skills}
- Career Goal: {goal}
Output: Ein prägnantes, professionelles GitHub-README...
---

Image Models (Gemini/SD/FLUX):
---
Template für "Portfolio Banner":
"Create a minimalistic, dark-themed banner for a {archetype} 
developer profile. Visual style: {style}. Color palette: {colors}.
Include abstract symbols for: {top_3_skills}. No text, no faces."
---
```

**Model-Spezifische Anpassungen:**
- Gemini: Natürlich-sprachlicher, beschreibender Stil
- Stable Diffusion: Keywords, negative prompts
- FLUX.1: Kürzere, prägnante Beschreibungen

#### 2.2.6 Model Connectors (BYOK-fähig)

**Unterstützte Modelle (Stand 2026):**

1. **Text/LLM:**
   - Google Gemini (Free & Pro API)
   - OpenAI GPT-4/GPT-4o
   - Anthropic Claude
   - Lokale LLMs (Ollama/LM Studio)

2. **Image Generation:**
   - Google Gemini/Imagen (Free & Pro)
   - OpenAI DALL-E 3
   - Stable Diffusion (self-hosted)
   - FLUX.1 (Schnell/Dev, self-hosted)
   - Midjourney (via API wenn verfügbar)

**BYOK-Architektur:**

```typescript
interface ModelConnector {
  provider: 'gemini' | 'openai' | 'sd_local' | 'flux_local';
  validateKey(apiKey: string): Promise<boolean>;
  generateText(prompt: string, apiKey: string): Promise<string>;
  generateImage(prompt: string, options: object, apiKey: string): Promise<Buffer>;
}
```

**Key-Handling:**
1. **User bringt eigenen Key:**
   - Frontend verschlüsselt Key (clientseitig)
   - Sendet verschlüsselten Key mit Request
   - Backend entschlüsselt und nutzt Key für Modell-Call
   - Key wird NICHT persistiert (nur in Session-Cache)

2. **User nutzt unseren Free Key (Gemini):**
   - Shared Gemini Free API Key (Rate-Limit 15 req/min)
   - Fair-Use-Queue-System
   - Fallback zu anderen Modellen wenn Limit erreicht

**Key-Validierung:**
```javascript
POST /api/v1/keys/validate
{
  "provider": "gemini",
  "apiKey": "encrypted_key"
}
Response:
{
  "valid": true,
  "tier": "free" | "pro",
  "rateLimit": { "requests": 15, "period": "minute" }
}
```

**Gemini Free Tier Details (2026):**
- Rate Limits: 15 requests/min, 1500 requests/day
- Image Generation: 100 images/day mit Imagen
- Kostenlos, keine Kreditkarte nötig
- Perfekt für Free Tier unserer Plattform

#### 2.2.7 Rendering & Packaging Service

**Aufgaben:**
1. Wasszeichen hinzufügen (Free Tier)
2. User-Bilder/Logos einbinden
3. Text-Overlays (Name, Username)
4. ZIP-Paket erstellen:
   - README.md
   - profile-banner.png
   - repo-covers/ (3-5 Bilder)
   - social-cards/ (LinkedIn, Twitter)
   - instructions.md

**Temporärer Storage:**
- S3/MinIO mit Presigned URLs
- TTL: 4 Stunden
- Auto-Delete nach Download oder TTL

#### 2.2.8 Analytics DB (Nur Aggregiert)

**Was wir speichern:**

```sql
-- generation_stats
CREATE TABLE generation_stats (
  id UUID PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  template_id VARCHAR(50),
  model_provider VARCHAR(50),
  model_name VARCHAR(100),
  tier VARCHAR(20), -- free/pro/enterprise
  duration_ms INTEGER,
  success BOOLEAN,
  error_code VARCHAR(50)
);

-- ai_usage_buckets (anonymisiert)
CREATE TABLE ai_usage_buckets (
  id UUID PRIMARY KEY,
  date DATE NOT NULL,
  language VARCHAR(50),
  ai_bucket VARCHAR(20), -- 0_10, 10_30, 30_60, 60_100
  sample_size INTEGER,
  archetype VARCHAR(50)
);

-- trend_snapshots (voraggregiert)
CREATE TABLE trend_snapshots (
  id UUID PRIMARY KEY,
  date DATE NOT NULL,
  metric_name VARCHAR(100),
  metric_value JSONB,
  granularity VARCHAR(20) -- daily/weekly/monthly
);
```

**Was wir NICHT speichern:**
- GitHub-Usernames
- Repo-Namen
- Code-Snippets
- Commit-Messages
- Persönliche Präferenzen (außer in Session)
- API-Keys
- IP-Adressen (anonymisiert in Logs)

### 2.3 Tech Stack (State-of-the-Art 2026)

#### Frontend
- **Framework:** Next.js 14+ (App Router)
- **UI:** React 18+, Tailwind CSS 3+
- **Charts:** ECharts oder Recharts
- **State:** React Context + LocalStorage
- **API Client:** Axios + React Query

#### Backend
**Option A (Node.js):**
- NestJS (TypeScript)
- Redis (BullMQ für Jobs)
- PostgreSQL 15+

**Option B (Python):**
- FastAPI
- Celery (Redis als Broker)
- PostgreSQL 15+ oder ClickHouse

#### Infrastructure
- **Container:** Docker + Docker Compose
- **Orchestration:** Kubernetes (optional für Enterprise)
- **API Gateway:** Kong oder Traefik
- **Monitoring:** Prometheus + Grafana
- **Logging:** ELK Stack oder Loki
- **Tracing:** OpenTelemetry

#### AI/ML Stack
- **MLOps:** MLflow (Experiment Tracking, Model Registry)
- **LLM Libs:** LangChain, LlamaIndex (optional)
- **Image Gen:**
  - Stable Diffusion: ComfyUI oder A1111 WebUI + API
  - FLUX.1: Replicate API oder self-hosted
- **Context Engineering:** Custom Pipeline based on Survey

#### Storage
- **Object Store:** MinIO (self-hosted) oder S3
- **Cache:** Redis 7+
- **DB:** PostgreSQL 15+ (primary), ClickHouse (analytics)

#### Security
- **Secrets:** HashiCorp Vault oder AWS Secrets Manager
- **Encryption:** AES-256 für Keys (clientseitig)
- **Rate Limiting:** Redis + nginx
- **DDoS Protection:** Cloudflare (optional)

### 2.4 Deployment-Architektur

**Development:**
```
docker-compose.yml:
- frontend (Next.js)
- backend (NestJS/FastAPI)
- redis
- postgres
- minio
- mlflow-server
```

**Production (Cloud):**
```
- Frontend: Vercel oder Cloudflare Pages
- Backend: AWS ECS/EKS oder GCP Cloud Run
- Database: AWS RDS/Aurora oder GCP Cloud SQL
- Cache: AWS ElastiCache oder GCP Memorystore
- Object Storage: AWS S3 oder GCP Cloud Storage
- Image Gen Workers: GPU-enabled instances (NVIDIA T4/A10)
```

**Enterprise (On-Prem Option):**
```
Kubernetes Cluster:
- 3+ Control Plane Nodes
- 5+ Worker Nodes (CPU)
- 2+ GPU Nodes (Image Generation)
- Persistent Volumes für DB/Storage
```

---

## TEIL 3: ENTWICKLUNGS-ROADMAP

### Phase 1: MVP - Public Explorer (Wochen 1-8)

**Ziel:** Öffentliche Plattform, die aus GitHub-Username Basis-Infografiken generiert

**Features:**
- ✅ Frontend: Landing + Explorer Page
- ✅ GitHub Data Service (REST API)
- ✅ Basis Analytics (Activity, Languages, Top Repos)
- ✅ Einfache AI-Heuristik (Commit Messages)
- ✅ 1 Bild-Modell (Gemini Imagen mit Free API)
- ✅ Watermark-System
- ✅ 2 Templates ("Portfolio Card", "Skill Wheel")

**Deliverables:**
- Working Website
- Basic API Documentation
- Docker Compose Setup

### Phase 2: Profile Package Engine (Wochen 9-16)

**Features:**
- ✅ Vollständiges Scoring (4 Scores + Archetyp)
- ✅ Prompt Orchestrator (Context Engineering)
- ✅ LLM für README-Generierung
- ✅ 3+ Bild-Modelle (Gemini, SD, FLUX)
- ✅ ZIP-Packaging (README, Banner, Covers)
- ✅ 5+ Templates
- ✅ Public Insights Dashboard (aggregierte Stats)

**Deliverables:**
- Vollständiger Generierungsflow
- Analytics Dashboard
- API v1.0 stable

### Phase 3: BYOK & Pro Features (Wochen 17-24)

**Features:**
- ✅ BYOK-System (Frontend Encryption + Backend)
- ✅ Key-Validierung für alle Provider
- ✅ Pro Tier mit Payment (Stripe)
- ✅ 10+ Templates (Business, Strategy, Creative)
- ✅ Custom Styles & Colors
- ✅ MLflow Integration (Prompt Tracking)

**Deliverables:**
- BYOK Documentation
- Payment Integration
- Pro Tier Launch

### Phase 4: Enterprise & Data Products (Wochen 25-36)

**Features:**
- ✅ White-Label-Konfiguration
- ✅ Multi-Tenancy
- ✅ Admin Console
- ✅ Insights API (aggregierte Daten)
- ✅ Premium Reports (PDF Export)
- ✅ SSO/SAML (optional)
- ✅ On-Prem Deployment Option

**Deliverables:**
- Enterprise Version
- Data API
- Sales-ready Reports

---

## TEIL 4: API-SPEZIFIKATION (OpenAPI 3.0)

### 4.1 Core Endpoints

#### Analyze Profile
```yaml
POST /api/v1/public/analyze
Request:
{
  "github_username": "string",
  "preferences": {
    "career_goal": "string", // optional
    "style": "minimal|colorful|professional", // optional
    "colors": ["#hex1", "#hex2"] // optional
  },
  "byok": {
    "gemini_key": "encrypted_string", // optional
    "openai_key": "encrypted_string" // optional
  }
}

Response:
{
  "session_id": "uuid",
  "profile": {
    "username": "string",
    "avatar_url": "string",
    "bio": "string",
    "stats": {
      "repos": number,
      "followers": number,
      "contributions_last_year": number
    }
  },
  "scores": {
    "activity": number,
    "collaboration": number,
    "stack_diversity": number,
    "ai_savviness": number
  },
  "archetype": "string",
  "ai_analysis": {
    "bucket": "string",
    "by_language": {},
    "detected_tools": []
  }
}
```

#### Generate Package
```yaml
POST /api/v1/public/generate
Request:
{
  "session_id": "uuid",
  "template_id": "string",
  "model_preferences": {
    "text_model": "gemini-pro|gpt-4o|claude-3",
    "image_model": "gemini-imagen|dalle-3|sd-3.5|flux-schnell"
  },
  "assets": ["readme", "banner", "repo_covers", "social_cards"]
}

Response:
{
  "job_id": "uuid",
  "status": "queued|processing|completed|failed",
  "estimated_time_seconds": number
}

GET /api/v1/public/generate/:job_id
Response:
{
  "status": "completed",
  "download_url": "presigned_url",
  "expires_at": "timestamp",
  "assets": {
    "readme": "url",
    "banner": "url",
    "covers": ["url1", "url2"],
    "social_cards": ["url1", "url2"]
  }
}
```

#### Validate BYOK
```yaml
POST /api/v1/keys/validate
Request:
{
  "provider": "gemini|openai|anthropic",
  "api_key": "encrypted_string"
}

Response:
{
  "valid": boolean,
  "tier": "free|pro|enterprise",
  "rate_limits": {
    "requests_per_minute": number,
    "requests_per_day": number
  },
  "features": {
    "text_generation": boolean,
    "image_generation": boolean
  }
}
```

#### Public Insights
```yaml
GET /api/v1/public/insights?metric=ai_usage_by_language&period=30d
Response:
{
  "metric": "ai_usage_by_language",
  "period": "30d",
  "data": [
    {
      "language": "TypeScript",
      "buckets": {
        "0_10": 15,
        "10_30": 35,
        "30_60": 40,
        "60_100": 10
      },
      "sample_size": 1250
    }
  ],
  "updated_at": "timestamp"
}
```

---

## TEIL 5: SICHERHEIT & COMPLIANCE

### 5.1 Datenschutz (Privacy-First Design)

**Prinzipien:**
1. **Datenminimierung:** Nur was absolut nötig ist
2. **Temporäre Verarbeitung:** Max. 4h, dann Löschung
3. **Keine Personenidentifikation:** Nur Aggregation
4. **Transparenz:** Offene Dokumentation der Heuristiken

**GDPR-Konformität:**
- Kein Profiling (da keine Persistenz)
- Kein Cross-Site-Tracking
- User-Daten nur in RAM/Cache
- Klare ToS & Privacy Policy

### 5.2 API-Key-Security (BYOK)

**Client-seitige Verschlüsselung:**
```javascript
// Frontend
import CryptoJS from 'crypto-js';

function encryptApiKey(apiKey: string, sessionKey: string): string {
  return CryptoJS.AES.encrypt(apiKey, sessionKey).toString();
}

// Backend
function decryptApiKey(encrypted: string, sessionKey: string): string {
  const bytes = CryptoJS.AES.decrypt(encrypted, sessionKey);
  return bytes.toString(CryptoJS.enc.Utf8);
}
```

**Session-Key-Management:**
- Generiert bei Session-Start (CSPRNG)
- Nur im Browser-Memory (nicht LocalStorage)
- Wechselt bei jeder neuen Analyse

**Key-Validierung:**
- Test-Request an Provider-API
- Rate-Limit-Check
- Keine Persistenz nach Validierung

### 5.3 Rate Limiting & Abuse Prevention

**Limits (Free Tier):**
- 3 Analysen pro Tag pro IP
- 5 Analysen pro Tag pro GitHub-Username
- 1 aktive Generation pro Session

**Bot Protection:**
- hCaptcha oder Cloudflare Turnstile
- Fingerprinting (optional)
- Anomalie-Detektion (ungewöhnliche Request-Patterns)

### 5.4 GitHub API Compliance

**Rate Limits:**
- Unauthenticated: 60 req/h
- Authenticated (OAuth): 5000 req/h
- Enterprise: 15000 req/h

**Unsere Strategie:**
- Caching (15-30 Min TTL)
- Request-Bündelung (GraphQL)
- Fallback bei Rate-Limit-Hit

**ToS-Konformität:**
- Keine Massenscraper
- Respektierung von API-Limits
- Nur öffentliche Daten
- Attribution zu GitHub (Links)

---

## TEIL 6: DEPLOYMENT-GUIDE

### 6.1 Development Setup

```bash
# Clone Repository
git clone https://github.com/yourorg/gitprofileai.git
cd gitprofileai

# Environment Setup
cp .env.example .env
# Edit .env mit deinen Keys

# Docker Compose
docker-compose up -d

# Frontend
cd frontend
npm install
npm run dev

# Backend
cd backend
npm install
npm run start:dev

# Access
# Frontend: http://localhost:3000
# Backend: http://localhost:4000
# MLflow: http://localhost:5000
```

### 6.2 Production Deployment (Cloud)

**Option A: Vercel + AWS**
```
Frontend: Vercel (automatisch mit Git)
Backend: AWS ECS (Docker Container)
Database: AWS RDS PostgreSQL
Cache: AWS ElastiCache Redis
Storage: AWS S3
Workers: AWS EC2 GPU (g4dn.xlarge)
```

**Option B: GCP All-in**
```
Frontend: Cloud Run
Backend: Cloud Run
Database: Cloud SQL PostgreSQL
Cache: Memorystore Redis
Storage: Cloud Storage
Workers: Compute Engine GPU (NVIDIA T4)
```

### 6.3 Monitoring & Observability

**Metriken (Prometheus):**
- Request Rate/Latency
- Model Call Success Rate
- Generation Duration
- Queue Length
- Error Rate by Endpoint

**Dashboards (Grafana):**
- System Health
- User Flow Funnel
- Model Performance
- Cost per Generation

**Alerts:**
- High Error Rate (>5%)
- Model API Failures
- Queue Backlog (>50 Jobs)
- Database Connection Issues

---

## TEIL 7: KOSTEN-KALKULATION

### 7.1 Infrastructure Costs (Monatlich)

**Small Scale (1000 Users/Monat):**
- Frontend Hosting: $0 (Vercel Free)
- Backend: $50 (Cloud Run)
- Database: $20 (Cloud SQL)
- Storage: $5 (S3/GCS)
- Cache: $15 (Redis)
- **Total: ~$90/Monat**

**Medium Scale (10k Users/Monat):**
- Frontend: $20
- Backend: $200
- Database: $100
- Storage: $30
- Cache: $50
- GPU Workers: $200 (spot instances)
- **Total: ~$600/Monat**

**Large Scale (100k Users/Monat):**
- Frontend: $100
- Backend: $800
- Database: $400
- Storage: $150
- Cache: $200
- GPU Workers: $1500
- CDN: $100
- **Total: ~$3250/Monat**

### 7.2 Model API Costs (BYOK vs. Shared)

**User bringt eigenen Key:**
- Kosten = $0 für uns
- User zahlt direkt an Provider

**Shared Gemini Free:**
- Kostenlos bis zu Limits
- 100 Bilder/Tag = ~3000/Monat
- Bei Überschreitung: Fallback zu Pro (User-Upgrade)

**Einnahmen-Potenzial:**
- Free Tier: $0, aber Daten
- Pro Tier (15€/Monat): 1000 User = 15k€
- Enterprise: Custom Pricing (5k-50k€/Jahr)
- Data Reports: 10k-100k€/Jahr

---

## TEIL 8: NEXT STEPS FÜR ENTWICKLUNG

### Woche 1-2: Setup & Foundation
1. Repository Setup (Monorepo: Turborepo oder Nx)
2. Docker Compose Environment
3. CI/CD Pipeline (GitHub Actions)
4. Frontend Basis (Next.js App Router)
5. Backend Basis (NestJS + PostgreSQL)

### Woche 3-4: GitHub Integration
1. GitHub OAuth Setup
2. REST API Client
3. GraphQL Queries
4. Caching Layer (Redis)
5. Test mit echten Profilen

### Woche 5-6: Analytics & Scoring
1. Scoring-Algorithmen
2. AI-Heuristik (Commit-Analyse)
3. Archetyp-Klassifikation
4. Visualisierungen (Charts)

### Woche 7-8: Image Generation
1. Gemini Imagen Integration
2. Prompt Orchestrator
3. Template-System
4. Watermark-Service
5. MVP Launch 🚀

### Code-Struktur
```
gitprofileai/
├── apps/
│   ├── frontend/          # Next.js
│   ├── backend/           # NestJS
│   └── workers/           # Celery/BullMQ Workers
├── packages/
│   ├── shared-types/      # TypeScript Types
│   ├── ui-components/     # React Components
│   └── prompts/           # Prompt Templates
├── infra/
│   ├── docker/            # Dockerfiles
│   ├── k8s/               # Kubernetes Manifests
│   └── terraform/         # IaC
├── docs/
│   ├── api/               # OpenAPI Specs
│   ├── architecture/      # Diagrams
│   └── guides/            # Entwickler-Guides
└── scripts/
    ├── setup/
    └── deploy/
```

---

## TEIL 9: WISSENSCHAFTLICHE BASIS (Papers)

### Verwendete Research Papers:

1. **LIDA: Automatic Generation of Visualizations and Infographics**
   - Microsoft Research 2023
   - Basis für Prompt Orchestrator
   - Multi-Stage Generierung

2. **A Survey of Context Engineering for Large Language Models**
   - 2025, umfassende Taxonomie
   - Context Retrieval, Processing, Management
   - Basis für unseren Context Layer

3. **MLflow: Open Source ML Platform**
   - Databricks, kontinuierlich aktualisiert
   - Experiment Tracking
   - Model & Prompt Registry

4. **Integrated Visual Software Analytics on GitHub**
   - 2024, IEEE
   - GitHub-Metriken und Visualisierungen
   - Basis für Analytics Service

5. **Survey of Bias in Text-to-Image Generation**
   - 2024, arXiv
   - Fairness-Aspekte
   - Mitigation-Strategien für Prompts

---

## ZUSAMMENFASSUNG FÜR CLAUDE CODE

**Das Projekt in einem Satz:**
Wir bauen eine Privacy-First-Plattform, die aus GitHub-Profilen automatisch personalisierte Infografiken generiert (mit BYOK für alle gängigen AI-Modelle), dabei null Userdaten speichert, aber wertvolle anonyme KI-Nutzungsstatistiken sammelt, die wir monetarisieren.

**Tech-Stack-Kern:**
- Frontend: Next.js 14+ (TypeScript, Tailwind, React Query)
- Backend: NestJS oder FastAPI
- Database: PostgreSQL + Redis
- ML: MLflow + Custom Context Engineering
- Models: Gemini (Free!), OpenAI, Stable Diffusion, FLUX.1
- Deployment: Docker → Kubernetes oder Cloud Run

**Besonderheiten:**
- BYOK-Architektur mit Client-Encryption
- Zero-PII-Storage (nur anonyme Aggregation)
- Gemini Free als Basis (15 req/min, 100 img/day)
- State-of-the-Art Context Engineering
- Enterprise-ready von Tag 1

**Start hier:**
1. Lies diese Spec komplett
2. Setup Docker Compose
3. Implementiere GitHub Data Service
4. Baue Analytics & Scoring
5. Integriere Gemini Imagen
6. Launch MVP

**Bei Fragen:** Siehe Docs oder frag nach spezifischen Implementierungsdetails.

---

END OF SPECIFICATION

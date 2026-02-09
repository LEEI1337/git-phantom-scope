# GitProfileAI - Architecture Diagrams (PlantUML C4 Model)

## Installation & Verwendung

Diese Diagramme nutzen die C4-PlantUML Bibliothek.

**Online:**
- Gehe zu: http://www.plantuml.com/plantuml/uml/
- Kopiere den Code rein
- Oder nutze VS Code Extension: "PlantUML"

**Lokal:**
```bash
# Mit Docker
docker run -d -p 8080:8080 plantuml/plantuml-server:jetty
# Dann öffne http://localhost:8080
```

---

## Diagramm 1: System Context (C4 Level 1)

```plantuml
@startuml GitProfileAI_System_Context
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml

LAYOUT_WITH_LEGEND()

title System Context Diagram - GitProfileAI Platform

Person(developer, "Developer", "Möchte ein professionelles GitHub-Profil erstellen")
Person(recruiter, "Recruiter", "Sucht Entwickler und analysiert Profile")
Person(enterprise, "Enterprise User", "Nutzt Plattform für Team-Analytics")

System(gitprofileai, "GitProfileAI Platform", "Analysiert GitHub-Profile und generiert personalisierte Infografiken mit KI")

System_Ext(github, "GitHub API", "Stellt öffentliche Profildaten bereit")
System_Ext(gemini, "Google Gemini API", "Text- und Bildgenerierung (Free & Pro)")
System_Ext(openai, "OpenAI API", "GPT-4, DALL-E (BYOK)")
System_Ext(sd_local, "Self-Hosted SD", "Stable Diffusion / FLUX.1")

Rel(developer, gitprofileai, "Analysiert Profil, generiert Infografiken", "HTTPS")
Rel(recruiter, gitprofileai, "Holt Kandidaten-Übersichten", "HTTPS")
Rel(enterprise, gitprofileai, "Ruft Team-Analytics & Trend-Reports ab", "HTTPS/API")

Rel(gitprofileai, github, "Holt öffentliche Profildaten", "REST/GraphQL")
Rel(gitprofileai, gemini, "Generiert Texte & Bilder", "REST API")
Rel(gitprofileai, openai, "Generiert Texte & Bilder (BYOK)", "REST API")
Rel(gitprofileai, sd_local, "Generiert Bilder", "HTTP API")

@enduml
```

---

## Diagramm 2: Container Diagram (C4 Level 2)

```plantuml
@startuml GitProfileAI_Container
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

LAYOUT_WITH_LEGEND()

title Container Diagram - GitProfileAI Platform

Person(user, "User", "Developer/Recruiter/Enterprise")

System_Boundary(gitprofileai, "GitProfileAI Platform") {
    Container(web_app, "Web Application", "Next.js, React", "SPA mit Public Explorer, Generator, Insights Dashboard")
    Container(api_gateway, "API Gateway", "NestJS/FastAPI", "Routing, Rate Limiting, Auth, BYOK-Handling")

    Container(github_svc, "GitHub Data Service", "Node.js/Python", "Holt & cached GitHub-Daten, Rate-Limit-Management")
    Container(analytics_svc, "Analytics & Scoring", "Python", "Berechnet Scores, AI-Anteil, Archetypen")
    Container(prompt_svc, "Prompt Orchestrator", "Python", "Context Engineering, Template-Management")
    Container(model_svc, "Model Connectors", "Python", "BYOK-Integration, Multi-Provider-Support")
    Container(render_svc, "Rendering Service", "Node.js", "Watermarking, Packaging, ZIP-Generierung")

    ContainerDb(cache, "Session Cache", "Redis", "Session-State, GitHub-Cache (TTL 15-30min)")
    ContainerDb(analytics_db, "Analytics DB", "PostgreSQL", "Nur anonyme, aggregierte Statistiken")
    ContainerDb(object_store, "Object Storage", "S3/MinIO", "Temporäre ZIP-Pakete (TTL 4h)")

    Container(worker_queue, "Job Queue", "BullMQ/Celery", "Async Image Generation & Packaging")
    Container(mlflow, "MLflow Server", "MLflow", "Experiment Tracking, Prompt-Versionierung")
}

System_Ext(github_api, "GitHub API", "REST/GraphQL")
System_Ext(gemini_api, "Gemini API")
System_Ext(openai_api, "OpenAI API")
System_Ext(sd_worker, "SD Worker")

Rel(user, web_app, "Nutzt", "HTTPS")
Rel(web_app, api_gateway, "API Calls", "JSON/HTTPS")

Rel(api_gateway, github_svc, "Ruft Profildaten ab")
Rel(api_gateway, analytics_svc, "Berechnet Metriken")
Rel(api_gateway, prompt_svc, "Generiert Prompts")
Rel(api_gateway, worker_queue, "Queued Jobs")

Rel(github_svc, github_api, "Holt Daten", "REST/GraphQL")
Rel(github_svc, cache, "Cached Responses")

Rel(analytics_svc, analytics_db, "Speichert aggregierte Stats", "SQL")

Rel(prompt_svc, model_svc, "Sendet Prompts")
Rel(prompt_svc, mlflow, "Tracked Varianten")

Rel(model_svc, gemini_api, "Text/Image Gen", "REST")
Rel(model_svc, openai_api, "Text/Image Gen (BYOK)", "REST")
Rel(model_svc, sd_worker, "Image Gen", "HTTP")

Rel(worker_queue, render_svc, "Processing Jobs")
Rel(render_svc, object_store, "Speichert ZIP", "S3 API")
Rel(render_svc, web_app, "Download URL", "Presigned URL")

@enduml
```

---

## Diagramm 3: Component Diagram - API Gateway (C4 Level 3)

```plantuml
@startuml GitProfileAI_Component_APIGateway
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml

LAYOUT_WITH_LEGEND()

title Component Diagram - API Gateway (Detail)

Container(web_app, "Web Application", "Next.js")

Container_Boundary(api_gateway, "API Gateway") {
    Component(router, "Request Router", "NestJS Controller", "Routes requests zu Services")
    Component(rate_limiter, "Rate Limiter", "Redis-based", "3 req/day Free, 50 req/day Pro")
    Component(auth_handler, "Auth Handler", "JWT/API Key", "Validiert Tokens & API Keys")
    Component(byok_manager, "BYOK Manager", "Crypto Module", "Entschlüsselt & validiert User-Keys")
    Component(session_mgr, "Session Manager", "Redis Client", "Verwaltet Session-State (TTL 30min)")
    Component(logger, "Request Logger", "Winston/Pino", "Strukturierte Logs (anonymisiert)")
}

ContainerDb(redis, "Redis Cache")
Container(github_svc, "GitHub Data Service")
Container(analytics_svc, "Analytics Service")

Rel(web_app, router, "POST /api/v1/public/analyze", "JSON/HTTPS")

Rel(router, rate_limiter, "Check Limits")
Rel(rate_limiter, redis, "Get/Set Counters")

Rel(router, auth_handler, "Validate Token")
Rel(router, byok_manager, "Decrypt API Keys")

Rel(router, session_mgr, "Create/Get Session")
Rel(session_mgr, redis, "Store Session State")

Rel(router, github_svc, "Fetch GitHub Data")
Rel(router, analytics_svc, "Calculate Scores")

Rel(router, logger, "Log Request")

@enduml
```

---

## Diagramm 4: Sequence Diagram - Full Generation Flow

```plantuml
@startuml GitProfileAI_Sequence_Generation
!theme plain

title Sequence Diagram - Vollständiger Generierungsflow

actor User
participant "Web App" as Web
participant "API Gateway" as API
participant "GitHub Service" as GitHub
participant "Analytics" as Analytics
participant "Prompt Orch." as Prompt
participant "Model Connector" as Model
participant "Gemini API" as Gemini
participant "Worker Queue" as Queue
participant "Rendering" as Render
participant "S3/MinIO" as S3
database "Redis Cache" as Redis
database "Analytics DB" as DB

== Phase 1: Analyse ==

User -> Web: Gibt Username ein + Präferenzen
Web -> API: POST /analyze {"username": "torvalds", ...}
API -> Redis: Check Rate Limit
API -> GitHub: GET /users/torvalds + /repos
GitHub --> API: Public Profile Data (JSON)
API -> Redis: Cache Profil-Daten (TTL 15min)

API -> Analytics: Calculate Scores & AI-Usage
Analytics -> Analytics: Commit-Message-Analyse
Co-Author-Detection
Analytics --> API: Scores + Archetyp + AI-Bucket

API -> Redis: Store Session (TTL 30min)
API --> Web: {"session_id": "uuid", "scores": {...}, ...}
Web -> User: Zeigt Analyse + Vorschau

== Phase 2: Generierung ==

User -> Web: Wählt Template + Modell
Web -> API: POST /generate {"session_id": "uuid", ...}
API -> Redis: Get Session State
API -> Prompt: Create Prompts (Text + Image)
Prompt -> Prompt: Context Engineering
(Retrieval→Processing→Management)

API -> Queue: Enqueue Generation Job
API --> Web: {"job_id": "uuid", "status": "queued"}

Queue -> Model: Process Job
Model -> Gemini: POST /generateText (README)
Gemini --> Model: Generated README (Markdown)

Model -> Gemini: POST /generateImage (Banner)
Gemini --> Model: Generated Image (PNG)

Model -> Queue: Job Progress Update
Queue --> Web: WebSocket: {"progress": 60}

Model -> Render: Package Assets
Render -> Render: Add Watermark (Free Tier)
Render -> Render: Create ZIP Bundle

Render -> S3: Upload ZIP (Presigned URL, TTL 4h)
S3 --> Render: Download URL

Render -> Redis: Update Job Status = "completed"
Render --> Web: {"status": "completed", "download_url": "..."}

== Phase 3: Download & Cleanup ==

User -> Web: Klickt Download
Web -> S3: GET presigned URL
S3 --> User: Download ZIP

note over Redis: Session expired (30 min)
note over S3: ZIP auto-deleted (4h)

== Phase 4: Analytics (Anonym) ==

Render -> DB: INSERT generation_stats
(template, model, tier, duration)
Render -> DB: INSERT ai_usage_buckets
(language, bucket, sample_size)

@enduml
```

---

## Diagramm 5: Deployment Diagram - Production

```plantuml
@startuml GitProfileAI_Deployment
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Deployment.puml

LAYOUT_WITH_LEGEND()

title Deployment Diagram - Production (AWS/GCP)

Deployment_Node(cdn, "CDN", "Cloudflare") {
    Container(cdn_cache, "Static Assets", "Images, JS, CSS")
}

Deployment_Node(frontend_host, "Frontend Hosting", "Vercel/Cloudflare Pages") {
    Container(nextjs_app, "Next.js App", "SSR + Client")
}

Deployment_Node(cloud, "Cloud Provider", "AWS/GCP") {

    Deployment_Node(compute, "Compute (ECS/Cloud Run)") {
        Container(api_containers, "API Gateway", "NestJS Containers (Auto-Scaling)")
        Container(service_containers, "Microservices", "GitHub, Analytics, Prompt Services")
    }

    Deployment_Node(workers, "GPU Workers (EC2/Compute Engine)") {
        Container(model_workers, "Model Connectors", "Python Workers + GPU (NVIDIA T4)")
        Container(sd_container, "Stable Diffusion", "ComfyUI/A1111 API")
    }

    Deployment_Node(data, "Data Layer") {
        ContainerDb(rds, "PostgreSQL", "RDS/Cloud SQL")
        ContainerDb(elasticache, "Redis", "ElastiCache/Memorystore")
        ContainerDb(s3, "Object Storage", "S3/Cloud Storage")
    }

    Deployment_Node(ml, "ML Infrastructure") {
        Container(mlflow_server, "MLflow", "EC2/Compute Engine")
    }
}

Deployment_Node(monitoring, "Observability") {
    Container(prometheus, "Prometheus", "Metrics")
    Container(grafana, "Grafana", "Dashboards")
    Container(elk, "ELK Stack", "Logs")
}

Rel(cdn, nextjs_app, "Cached Assets")
Rel(nextjs_app, api_containers, "API Requests", "HTTPS")
Rel(api_containers, service_containers, "Internal Calls", "gRPC/HTTP")
Rel(service_containers, model_workers, "Model Requests", "Job Queue")
Rel(model_workers, sd_container, "Image Gen", "HTTP")
Rel(service_containers, rds, "Read/Write", "SQL")
Rel(service_containers, elasticache, "Cache", "Redis Protocol")
Rel(model_workers, s3, "Store Assets", "S3 API")
Rel(service_containers, mlflow_server, "Track Experiments")

Rel(api_containers, prometheus, "Metrics", "Pull")
Rel(prometheus, grafana, "Query", "PromQL")
Rel(service_containers, elk, "Logs", "Filebeat")

@enduml
```

---

## Diagramm 6: Data Flow - BYOK Security

```plantuml
@startuml GitProfileAI_BYOK_Flow
!theme plain

title Data Flow - BYOK (Bring Your Own Key) Security

actor User
participant "Browser" as Browser
participant "Encryption
(Client)" as Crypto
participant "API Gateway" as API
participant "BYOK Manager" as BYOK
participant "Session Cache
(Redis)" as Redis
participant "Model Connector" as Model
participant "External API
(Gemini/OpenAI)" as External

== Key Input & Encryption ==

User -> Browser: Gibt API-Key ein
(z.B. Gemini Free Key)
Browser -> Crypto: encryptKey(apiKey, sessionSecret)
note right of Crypto
  AES-256 Encryption
  sessionSecret = CSPRNG()
  Nie im LocalStorage!
end note
Crypto --> Browser: encryptedKey (Base64)

== Key Validation ==

Browser -> API: POST /keys/validate
{"provider": "gemini", "key": "enc..."}
API -> BYOK: validateKey(encryptedKey)
BYOK -> BYOK: Decrypt with sessionSecret
BYOK -> External: Test Request (minimal)
External --> BYOK: 200 OK + Tier Info
BYOK --> API: {"valid": true, "tier": "free"}
API --> Browser: Validation Success

== Key Usage (Generation) ==

Browser -> API: POST /generate
{"session_id": "...", "byok": {"gemini_key": "enc..."}}
API -> BYOK: Decrypt Key
BYOK -> Redis: Store in Session (TTL 30min)
note right of Redis
  Key existiert nur in:
  1. Session Cache (30min)
  2. Memory während Request

  NIEMALS in:
  - Database
  - Logs
  - Disk
end note

API -> Model: Generate with Key
Model -> Redis: Get Key from Session
Redis --> Model: Decrypted Key (Memory only)
Model -> External: POST /generate
Authorization: Bearer {key}
External --> Model: Generated Content
Model -> Model: Clear Key from Memory
Model --> API: Result

== Session Expiry ==

Redis -> Redis: TTL expired (30min)
Redis -> Redis: Auto-delete Key

note over Browser, Redis
  User muss Key bei neuer
  Session erneut eingeben
end note

@enduml
```

---

## Verwendung der Diagramme

### VS Code Extension:
1. Installiere "PlantUML" Extension
2. Öffne diese Datei
3. Rechtsklick → "Preview Current Diagram"

### Online Editor:
1. Gehe zu: http://www.plantuml.com/plantuml/uml/
2. Kopiere einen Diagramm-Block
3. Paste & Generiere

### Export als PNG/SVG:
```bash
# Mit Docker
docker run --rm -v $(pwd):/data plantuml/plantuml:latest -tpng /data/architecture.puml
```

### In Confluence/Notion:
- Nutze PlantUML-Plugins
- Oder exportiere als PNG und füge ein

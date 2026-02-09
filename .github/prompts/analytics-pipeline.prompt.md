---
name: "analytics-pipeline"
description: "Build and maintain the anonymous analytics pipeline for aggregated AI trend data and developer archetype distribution insights."
mode: "agent"
---

# Analytics Pipeline

## Context
Build the anonymous analytics system that captures aggregated trends WITHOUT any personally identifiable information. This data powers the "AI in Open Source" trend reports.

## Data Flow
```
Profile Analysis --> Anonymization Layer --> PostgreSQL (aggregated only)
                          |
                          v
                   Strip ALL PII:
                   - No usernames
                   - No emails
                   - No repo names
                   - No commit hashes
                   - Only: scores, archetype, languages, AI %
```

## PostgreSQL Schema (Analytics ONLY)
```sql
-- ALLOWED: Anonymous aggregated data
CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,       -- 'profile_analyzed', 'package_generated'
    archetype VARCHAR(100),                 -- 'AI-Driven Indie Hacker'
    activity_score_bucket INT,             -- Rounded to nearest 10
    collab_score_bucket INT,
    diversity_score_bucket INT,
    ai_savviness_bucket INT,
    ai_percentage_bucket INT,              -- Rounded to nearest 5
    top_languages JSONB,                   -- ['Python', 'TypeScript'] (no repo context)
    tools_detected JSONB,                  -- ['GitHub Copilot']
    template_used VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- FORBIDDEN columns (never add):
-- username, email, github_id, ip_address, session_id, repo_names
```

## Aggregation Queries
```sql
-- AI usage trends over time
SELECT
    DATE_TRUNC('week', created_at) AS week,
    AVG(ai_percentage_bucket) AS avg_ai_percentage,
    COUNT(*) AS analyses_count
FROM analytics_events
WHERE event_type = 'profile_analyzed'
GROUP BY week
ORDER BY week DESC;

-- Archetype distribution
SELECT
    archetype,
    COUNT(*) AS count,
    AVG(ai_savviness_bucket) AS avg_ai_score
FROM analytics_events
GROUP BY archetype
ORDER BY count DESC;
```

## Privacy Guarantees
- Score values are bucketed (rounded) to prevent fingerprinting
- Minimum k-anonymity: events only stored if >10 similar profiles exist
- No temporal correlation possible (created_at has day precision only)
- Retention: 365 days maximum, then aggregated further

## Implementation Files
- `backend/services/analytics_service.py` - Event recording
- `backend/db/models.py` - SQLAlchemy models
- `backend/api/v1/routes/insights.py` - Public trend API
- `backend/db/migrations/` - Alembic migrations

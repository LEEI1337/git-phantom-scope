---
name: "analyze-github-profile"
description: "Analyze a public GitHub profile: fetch repos, languages, contributions, commit patterns, and generate a comprehensive scoring report."
mode: "agent"
---

# Analyze GitHub Profile

## Context
You are analyzing a public GitHub profile to generate comprehensive developer intelligence. This is the core skill of Git Phantom Scope.

## Task
Given a GitHub username, perform a complete profile analysis:

1. **Fetch Profile Data** via GitHub REST + GraphQL API:
   - User metadata (bio, location, created_at, public_repos count)
   - All public repositories (name, language, stars, forks, last_push)
   - Contribution graph data (commits per day/week/month)
   - Top languages by bytes of code

2. **Calculate Scoring Dimensions** (0-100 each):
   - **Activity Score**: Commit frequency, streak length, recency, repo creation rate
   - **Collaboration Score**: PRs opened/merged, issues created, code reviews, forks received
   - **Stack Diversity**: Number of unique languages, frameworks detected, tool variety
   - **AI-Savviness**: Co-author tags (GitHub Copilot, AI tools), AI-pattern commit messages

3. **Classify Developer Archetype** based on score combination:
   - Map score patterns to archetype labels
   - Include confidence percentage

4. **Generate Summary Report** as JSON:
   ```json
   {
     "username": "...",
     "scores": {"activity": 85, "collaboration": 72, "diversity": 91, "ai_savviness": 68},
     "archetype": {"label": "Full-Stack Polyglot", "confidence": 0.87},
     "top_languages": [...],
     "ai_detection": {"estimated_ai_percentage": 23, "tools_detected": ["GitHub Copilot"]},
     "generated_at": "ISO timestamp"
   }
   ```

## Privacy Rules
- NEVER store the username or profile data in PostgreSQL
- Cache results in Redis with 30-minute TTL only
- Strip any email addresses from the response
- Do not include private repo data (even if accessible)

## Implementation Files
- `backend/services/github_service.py` - GitHub API client
- `backend/services/scoring_engine.py` - Scoring calculations
- `backend/api/v1/routes/analyze.py` - API endpoint
- `backend/skills/templates/` - Analysis templates

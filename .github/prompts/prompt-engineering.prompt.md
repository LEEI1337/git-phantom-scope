---
name: "prompt-engineering"
description: "Design and optimize prompts for AI model interactions including profile summaries, archetype descriptions, and infographic text generation."
mode: "agent"
---

# Prompt Engineering

## Context
Design context-engineered prompts for the multi-model AI pipeline. Prompts must work across Gemini, OpenAI, and other BYOK models.

## Prompt Categories

### 1. Profile Summary Generation
Generate a compelling developer summary from scoring data:
```
System: You are a developer profiling assistant. Generate a concise, engaging
developer summary based on the provided scoring data. Be specific about
strengths and unique characteristics. Maximum 3 sentences.

Input: {scores_json}
Output: A compelling 2-3 sentence developer summary.
```

### 2. Archetype Description
Generate archetype-specific descriptions:
```
System: You are a developer archetype specialist. Given the archetype label
and scoring breakdown, write a 2-paragraph description that explains:
1. What this archetype means and its strengths
2. Specific advice for growth based on lower scores

Tone: Professional but approachable. No jargon.
```

### 3. Infographic Text Blocks
Generate text content for infographic elements:
- Headline (max 8 words)
- Subheadline (max 15 words)
- Stat callouts (score + short descriptor)
- Footer CTA

### 4. README Template Generation
Generate personalized GitHub profile README content:
```
System: Generate a GitHub profile README.md using the provided developer
data. Include: greeting, about section, tech stack badges, stats,
and recent activity. Style: {user_preference}.
```

## MLflow Integration
- Version all prompts with MLflow experiment tracking
- A/B test prompt variants
- Track token usage and response quality metrics
- Store prompt templates (NOT user data) in PostgreSQL

## Model-Agnostic Rules
- Prompts must work with temperature 0.3-0.7
- Max input tokens: 2000 (to fit all models)
- Max output tokens: 500 for summaries, 1500 for READMEs
- Always include system prompt with role definition
- Never include PII in prompt context

## Implementation Files
- `backend/services/prompt_orchestrator.py` - Prompt pipeline
- `backend/skills/templates/prompts/` - Prompt templates
- `backend/services/mlflow_tracker.py` - Experiment tracking

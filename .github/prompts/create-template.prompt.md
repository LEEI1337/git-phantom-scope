---
name: "create-template"
description: "Create new infographic and visual identity templates with layout definitions, color schemes, and rendering configurations."
mode: "agent"
---

# Create Template

## Context
Design and implement new visual identity templates for the infographic generation system. Templates define layout, colors, fonts, and content placement.

## Template Structure
Each template is a directory under `backend/skills/templates/`:
```
templates/
  dark-neon/
    config.json         # Layout, colors, fonts, dimensions
    preview.png         # Template preview thumbnail (400x210)
    elements.json       # Individual element definitions
    README.md           # Template documentation
  light-minimal/
    ...
  gradient-wave/
    ...
```

## Config Schema
```json
{
  "name": "dark-neon",
  "display_name": "Dark Neon",
  "version": "1.0.0",
  "tier": "free",
  "dimensions": {
    "width": 1200,
    "height": 630
  },
  "colors": {
    "background": "#0D1117",
    "primary": "#58A6FF",
    "secondary": "#8B949E",
    "accent": "#39D353",
    "text": "#F0F6FC",
    "chart_colors": ["#58A6FF", "#39D353", "#F78166", "#D2A8FF"]
  },
  "fonts": {
    "heading": {"family": "Inter", "weight": 700, "size": 32},
    "subheading": {"family": "Inter", "weight": 500, "size": 18},
    "body": {"family": "JetBrains Mono", "weight": 400, "size": 14},
    "stats": {"family": "JetBrains Mono", "weight": 700, "size": 48}
  },
  "layout": {
    "padding": 40,
    "sections": [
      {"type": "header", "y": 0, "height": 120},
      {"type": "scores_radar", "y": 130, "height": 300},
      {"type": "languages_bar", "y": 440, "height": 80},
      {"type": "footer", "y": 540, "height": 90}
    ]
  },
  "elements": {
    "radar_chart": {"type": "radar", "position": {"x": 40, "y": 130}},
    "archetype_badge": {"type": "badge", "position": {"x": 700, "y": 50}},
    "ai_percentage": {"type": "stat_callout", "position": {"x": 700, "y": 300}},
    "language_bars": {"type": "horizontal_bar", "position": {"x": 40, "y": 440}},
    "watermark": {"type": "text", "position": {"x": 1100, "y": 600}, "tier_gate": "free"}
  }
}
```

## Available Template Tiers
- **Free**: 2 templates (dark-neon, light-minimal)
- **Pro**: 10+ templates (gradient-wave, retro-terminal, corporate-clean, etc.)
- **Enterprise**: Custom templates, white-label support

## Design Requirements
- All templates must render correctly with any score combination (0-100)
- Text must be readable at 50% zoom
- Color contrast must meet WCAG AA standards
- Fonts must be bundled (not system-dependent)
- Templates must support both "with AI data" and "without AI data" variants

## Implementation Files
- `backend/skills/templates/` - Template directories
- `backend/services/renderer.py` - Template rendering engine
- `backend/services/template_registry.py` - Template discovery/loading

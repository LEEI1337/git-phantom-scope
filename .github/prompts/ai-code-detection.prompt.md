---
name: "ai-code-detection"
description: "Detect AI-assisted code patterns in GitHub repositories using heuristic analysis of commits, co-author tags, and code patterns."
mode: "agent"
---

# AI Code Detection

## Context
Detect and quantify AI-assisted code within GitHub repositories. This is a unique differentiator for Git Phantom Scope.

## Detection Heuristics

### 1. Co-Author Tag Analysis
Scan commit messages for co-author tags indicating AI tool usage:
```
Co-authored-by: GitHub Copilot <copilot@github.com>
Co-authored-by: Cursor <cursor@cursor.sh>
```

### 2. Commit Message Pattern Analysis
Detect AI-generated commit messages by pattern:
- Generic messages: "Update file", "Fix bug", "Add feature"
- Structured patterns: "feat:", "fix:", "chore:" (could be conventional commits OR AI)
- Unusually long, well-formatted descriptions for small changes
- Repeated patterns across many commits

### 3. Code Pattern Analysis (Lightweight)
- Unusually consistent formatting across files
- Comment density analysis (AI tends to over-comment or under-comment)
- Import pattern analysis (AI tends to import more than needed)
- Variable naming consistency analysis

### 4. Temporal Analysis
- Burst commit patterns (many commits in short timeframes)
- Unusual commit hours for the user's timezone
- Large code additions with minimal subsequent fixes

## Output Format
```json
{
  "ai_percentage_estimate": 23,
  "confidence": 0.72,
  "tools_detected": [
    {"tool": "GitHub Copilot", "evidence_count": 15, "confidence": 0.95},
    {"tool": "ChatGPT/Claude", "evidence_count": 3, "confidence": 0.45}
  ],
  "per_repo_breakdown": [
    {"repo": "project-a", "ai_percentage": 45, "evidence": ["co-author tags", "commit patterns"]},
    {"repo": "project-b", "ai_percentage": 5, "evidence": ["minimal indicators"]}
  ],
  "methodology": "heuristic-v1",
  "disclaimer": "Estimates based on public signals. Actual AI usage may differ."
}
```

## Privacy Rules
- Only analyze publicly available data
- Do not make definitive claims about AI usage
- Always include methodology disclaimer
- Never store results persistently

## Implementation Files
- `backend/services/ai_detection.py` - Detection engine
- `backend/services/commit_analyzer.py` - Commit pattern analysis
- `backend/skills/templates/ai_report.py` - Report templates

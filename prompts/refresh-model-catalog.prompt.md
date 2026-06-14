---
description: "Regenerate the model catalog cache with environment discovery and telemetry"
agent: "agent"
---

## Refresh Orchestrator Model Catalog

Refresh the model catalog cache on demand using environment discovery, GitHub Copilot session telemetry, and telemetry calibration.

### What Gets Refreshed

Run `scripts/refresh_model_catalog.py` from the workspace root to regenerate:

- `skills/model_catalog.json` (root workspace)
- `.github/agents/Orchestrator/skills/model_catalog.json` (mirrored copy for nested orchestrator)

### How It Works

1. **Environment Discovery** — Enumerates available models from the active environment
2. **GitHub Copilot Session Telemetry** — Reads `~/.copilot/session-state/**/events.jsonl` for `selectedModel`, `currentModel`, and `modelMetrics`
3. **Telemetry Calibration** — Normalizes provider-specific metrics on 0-100 scale:
   - `quality_score` — pass quality + contract completeness
   - `latency_score` — p95 end-to-end latency (inverse normalized)
   - `cost_score` — blended token + tool overhead cost (inverse normalized)
   - `tool_call_reliability` — success rate trend over 14-day window

### Model Catalog Schema

Each model entry includes:

```json
{
  "model_id": "gpt-4o",
  "capability_tier": "frontier",
  "quality_score": 92,
  "latency_score": 78,
  "cost_score": 65,
  "context_window": 128000,
  "tool_call_reliability": "pass",
  "recency_window_days": 14,
  "sample_size": 35,
  "calibration_confidence": "high"
}
```

### Validation

After refresh, verify:
- Catalog parses as valid JSON
- Contains at least one model entry
- Each model has required fields (model_id, capability_tier, context_window)
- Scores are in 0-100 range

### Related Policies

- See `rules/Model.Policy.md` for scoring formulas, calibration windows, and reliability adjustments
- Fallback behavior: if discovery fails or telemetry is missing, switch to `strict-deterministic` mode
- Do not manually edit `model_catalog.json`; always regenerate via script
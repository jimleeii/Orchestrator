---
description: "Alias for /refresh-model-catalog — regenerate the model catalog cache"
agent: "agent"
---

Alias for `/refresh-model-catalog`. Refresh the Orchestrator model catalog cache on demand.

See `/refresh-model-catalog` for full documentation on environment discovery, telemetry calibration, and schema.

### Quick Reference

Run `scripts/refresh_model_catalog.py` from the workspace root to regenerate:

- `skills/model_catalog.json`
- `.github/agents/Orchestrator/skills/model_catalog.json` (mirrored)

Then verify the cache contains valid model entries with quality, latency, and cost scores.

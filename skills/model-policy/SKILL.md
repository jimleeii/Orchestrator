---
name: model-policy
description: "Model selection, discovery, scoring, and fallback strategies for cost/latency vs correctness tradeoffs."
---

# Model Policy

Purpose: define how the orchestrator discovers candidate models, calibrates scores,
enforces criticality-based guardrails, and applies deterministic fallbacks when
adaptive scoring is unavailable.

This skill summarizes the canonical policy in `../../rules/Model.Policy.md` and is
the operational guidance for runtime selection behavior.

## Operating Modes

The orchestrator supports two routing modes.

- Default mode: `adaptive-score-based`
- Alternative mode: `strict-deterministic`

Mode switch triggers:

- User explicitly requests strict mode.
- A reliability incident requires predictable tier ordering.
- Model catalog or telemetry is unavailable/stale for current cycle.

Mode behavior summary:

- Adaptive mode uses weighted scoring and reliability adjustment.
- Strict mode uses fixed tier priorities by task type.
- The runtime records both `persistent_mode` and `effective_mode` per cycle.

## Environment Discovery

Before dispatching subagents in each orchestration cycle, run this discovery
pipeline.

1. Enumerate currently available models in the active environment.
2. Build or refresh a model catalog.
3. Apply hard constraints and mark ineligible models.

Telemetry source for calibration and recency checks:

- GitHub Copilot session telemetry from
    `~/.copilot/session-state/**/events.jsonl`

Required model catalog fields:

- `model_id`
- `capability_tier` (`frontier`, `balanced`, `economy`)
- `quality_score` (0-100)
- `latency_score` (0-100, higher is faster)
- `cost_score` (0-100, higher is cheaper)
- `context_window`
- `tool_call_reliability`

Hard constraints (ineligibility rules):

- Required tool-calling support is missing.
- Context window is insufficient for task payload size.
- Repeated recent hard failures on similar tasks.

If discovery fails for the cycle, use `strict-deterministic` mode and emit a
fallback reason.

## Score Calibration and Normalization

Normalize provider telemetry before adaptive scoring so candidates are comparable
across backends.

Calibration window rules:

- Rolling window: 14 days.
- Minimum sample size: 20 completed tasks per model for high confidence.
- If sample size is below 20, blend observed values with priors:
    - prior weight: 0.60
    - observed weight: 0.40

Normalization rules (all scores on 0-100 scale):

- Quality uses direct normalization.
- Latency uses inverse normalization.
- Cost uses inverse normalization.

Reference formulas:

- `normalized = 100 * (x - min_x) / (max_x - min_x)`
- `inverse_normalized = 100 * (max_x - x) / (max_x - min_x)`
- If `max_x == min_x`, assign neutral score `50`.

Reliability adjustment:

- Compute `reliability_factor = clamp(success_rate_30d, 0.85, 1.05)`.
- Compute `final_selection_score = selection_score * reliability_factor`.
- If model has two or more recent hard failures on similar tasks, mark
    ineligible even with a high score.

Missing-data defaults:

- Missing latency telemetry → set `latency_score = 50` and mark
    `telemetry_partial = true`.
- Missing cost telemetry → set `cost_score = 50` and mark
    `telemetry_partial = true`.
- Missing quality telemetry → block dispatch in adaptive mode and use strict
    fallback behavior when required.

Calibration metadata to log:

- `telemetry_window_days`
- `sample_size`
- `telemetry_partial`

```yaml
pseudocode_score_calibration_normalization: |
    # Constants
    CAL_WINDOW_DAYS = 14
    MIN_SAMPLE_SIZE = 20
    PRIOR_WEIGHT = 0.60
    OBSERVED_WEIGHT = 0.40
    RELIABILITY_MIN = 0.85
    RELIABILITY_MAX = 1.05
    NEUTRAL_SCORE = 50

    function clamp(value, min_value, max_value):
        return max(min_value, min(max_value, value))

    function normalize(value, min_x, max_x):
        if max_x == min_x:
            return NEUTRAL_SCORE
        return 100 * (value - min_x) / (max_x - min_x)

    function inverse_normalize(value, min_x, max_x):
        if max_x == min_x:
            return NEUTRAL_SCORE
        return 100 * (max_x - value) / (max_x - min_x)

    function blend_with_prior(observed, prior):
        return PRIOR_WEIGHT * prior + OBSERVED_WEIGHT * observed

    function calibrate_model_scores(model_stats, global_priors, minmax):
        sample_size = model_stats.sample_size or 0
        telemetry_partial = false

        if sample_size < MIN_SAMPLE_SIZE:
            quality_raw = blend_with_prior(
                model_stats.quality_raw or global_priors.quality,
                global_priors.quality,
            )
            latency_raw = blend_with_prior(
                model_stats.latency_raw or global_priors.latency,
                global_priors.latency,
            )
            cost_raw = blend_with_prior(
                model_stats.cost_raw or global_priors.cost,
                global_priors.cost,
            )
            telemetry_partial = true
        else:
            quality_raw = model_stats.quality_raw
            latency_raw = model_stats.latency_raw
            cost_raw = model_stats.cost_raw

        if quality_raw is null:
            quality_score = NEUTRAL_SCORE
            telemetry_partial = true
        else:
            quality_score = normalize(quality_raw, minmax.quality.min, minmax.quality.max)

        if latency_raw is null:
            latency_score = NEUTRAL_SCORE
            telemetry_partial = true
        else:
            latency_score = inverse_normalize(latency_raw, minmax.latency.min, minmax.latency.max)

        if cost_raw is null:
            cost_score = NEUTRAL_SCORE
            telemetry_partial = true
        else:
            cost_score = inverse_normalize(cost_raw, minmax.cost.min, minmax.cost.max)

        success_rate_30d = model_stats.success_rate_30d or global_priors.success_rate_30d
        reliability_factor = clamp(success_rate_30d, RELIABILITY_MIN, RELIABILITY_MAX)

        return {
            quality_score: quality_score,
            latency_score: latency_score,
            cost_score: cost_score,
            reliability_factor: reliability_factor,
            telemetry_partial: telemetry_partial,
            sample_size: sample_size,
        }
```

## Adaptive Score-Based Selection

For each eligible model, compute:

- `score = w_quality × quality + w_latency × latency + w_cost × cost`

Use the following per-subagent weights.

| Subagent | `w_quality` | `w_latency` | `w_cost` |
|---|---:|---:|---:|
| Software Architect | 0.60 | 0.15 | 0.25 |
| Senior Developer | 0.50 | 0.25 | 0.25 |
| Code Reviewer | 0.65 | 0.20 | 0.15 |

Selection rules:

- Select highest score among eligible candidates.
- If top two are within 3 points, prefer lower cost.
- For P0 critical tasks, enforce non-`economy` tier unless no alternative
    candidate is available.
- Emit top candidates and selection rationale in the cycle report.

## Strict Deterministic Fallback

When strict mode is active, select by fixed priority for task type.

| Task Type | Priority 1 | Priority 2 | Priority 3 |
|---|---|---|---|
| Architecture/design | `frontier` | `balanced` | `economy` |
| Implementation | `balanced` | `frontier` | `economy` |
| Review/security | `frontier` | `balanced` | `economy` |
| Direct/simple response | `economy` | `balanced` | `frontier` |

Strict-mode rules:

- Pick first available model in tier priority order.
- Do not re-rank within a tier.
- On model failure, retry once with next tier.
- Always log fallback reason and replacement model.

## Task Criticality Classifier

Criticality determines minimum tier enforcement.

| Criticality | Typical Task Type | Minimum Tier | Policy |
|---|---|---|---|
| `P0` | Security, incident mitigation, final high-risk gate | `frontier` | No `economy`; only controlled fallback to `balanced` |
| `P1` | Architecture decisions, compliance-sensitive refactors | `balanced` | Prefer `frontier`; avoid `economy` |
| `P2` | Standard implementation and routine review | `balanced` | Balanced preferred; economy allowed if guardrails pass |
| `P3` | Non-binding summaries or low-risk docs | `economy` | Any tier allowed based on availability/cost |

Classification rules:

- Default to `P2` when ambiguous.
- Elevate to `P0` for security risk, data-loss risk, or deployment-blocking
    decisions.
- Elevate to `P1` for architecture gate and design approval work.
- Downgrade to `P3` only for non-code, non-production-impacting analysis.

Enforcement behavior:

- Reject candidates below minimum tier.
- If no candidate satisfies minimum tier:
    - strict mode → return blocked and request explicit user override.
    - adaptive mode → perform one controlled fallback attempt, then block.
- Include `criticality` and `minimum_tier_enforced` in report output.

## Mode Control Interface

Supported user control phrases:

- `force strict for this run`
- `force strict until changed`
- `return to adaptive`
- `adaptive for this run`
- `show model routing mode`
- `approve temporary tier override for this run`
- `approve temporary tier override until changed`
- `clear tier override`

Control behavior:

- One-run controls apply only to current orchestration cycle.
- Until-changed controls update persisted routing state.
- `show model routing mode` returns active mode, persistent mode, and source.
- Tier overrides must emit explicit risk notes in dispatch and behavior logs.

State tracking requirements:

- Track `persistent_mode` and `effective_mode` for every cycle.
- Track mode source: `default`, `user-override`, or `fallback-on-failure`.
- Persist mode state via runbook checkpoint according to workspace policy.

## Guardrails and Model Selection Logic

Always enforce these guardrails:

- Do not use `economy` for final quality gates when `frontier` or `balanced`
    is available.
- Do not optimize cost over contract completeness.
- Prefer quality over speed when confidence is low.
- Keep policy changes small, reversible, and auditable.

Blocked-decision escalation flow:

1. Refresh discovery once.
2. Retry selection once with same criticality and mode.
3. If still blocked, return structured blocked status with reason and safe
     override phrase (if permitted).
4. Wait for user decision before dispatch.

Auto-retry limits and override constraints:

- Maximum one discovery refresh and one reselection attempt.
- Never silently dispatch below minimum tier.
- Do not auto-retry policy hard-stops (for example P0 with no qualifying tier).
- P0 tasks cannot be overridden down to `economy`.

## Related References

- Authoritative policy: `../../rules/Model.Policy.md`
- Environment discovery helper: `../../scripts/discover_models.py`
- Model catalog refresh helper: `../../scripts/refresh_model_catalog.py`


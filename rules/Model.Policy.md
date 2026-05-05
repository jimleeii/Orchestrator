## Model Selection Policy

Purpose: Encapsulate model discovery, scoring, and deterministic fallback behavior.

Essentials:

- Adaptive mode remains the default (`adaptive-score-based`) but fallbacks should be simpler when telemetry is partial: prefer `capability + recent_success`.
- Calibration windows and scoring formulas live here; keep weights per subagent but make them configurable.
- Minimum-tier enforcement (P0..P3) and escalation rules are defined here.

Simplified fallback rule (when telemetry missing or sparse):

1. Filter by required capabilities (tool-calling, context window).
2. Prefer models with recent success on similar tasks (recency window configurable).
3. If tie, prefer lower-cost model only when selection confidence is high.

Change process: Major changes to scoring or criticality require a runbook checkpoint and two acceptance tests demonstrating no regressions.

## Full Model Selection Policy (migrated)

### Operating Modes

- Default mode: `adaptive-score-based`
- Alternative mode: `strict-deterministic`
- Mode switch triggers:
  - User explicitly requests strict mode
  - Reliability incident requires predictable routing
  - Model catalog/telemetry is unavailable or stale

### Environment Discovery

Before dispatching subagents in each orchestration cycle:

1. Enumerate currently available models from the active environment.
2. Build/update a model catalog with these fields:

- `model_id`
- `capability_tier` (`frontier`, `balanced`, `economy`)
- `quality_score` (0-100)
- `latency_score` (0-100, higher is faster)
- `cost_score` (0-100, higher is cheaper)
- `context_window`
- `tool_call_reliability` (pass/fail trend)

3. Mark any model as ineligible if it fails hard constraints:

- Required tool-calling support missing
- Context window insufficient for the task
- Repeated recent failures for similar tasks

If discovery fails, switch to `strict-deterministic` mode for that cycle.

### Score Calibration and Normalization

Normalize provider telemetry before adaptive scoring so models from different backends are comparable.

Calibration window:

- Use rolling 14-day telemetry when available.
- Require at least 20 completed tasks per model for high-confidence calibration.
- If sample size is below 20, blend with global priors using 60% prior, 40% observed.

Normalization rules (all outputs on 0-100 scale):

- `quality_score`: map rubric pass quality and contract completeness to 0-100.
- `latency_score`: convert p95 end-to-end latency with inverse min-max normalization.
- `cost_score`: convert blended per-task cost (token and tool overhead) with inverse min-max normalization.

Reference formulas:

- `normalized = 100 * (x - min_x) / (max_x - min_x)`
- `inverse_normalized = 100 * (max_x - x) / (max_x - min_x)`
- If `max_x == min_x`, assign neutral score `50`.

Reliability adjustment:

- Apply a reliability multiplier after weighted score:
  - `reliability_factor = clamp(success_rate_30d, 0.85, 1.05)`
  - `final_selection_score = selection_score * reliability_factor`
- If a model has 2+ recent hard failures in similar tasks, mark ineligible regardless of score.

Missing data defaults:

- Missing latency telemetry: set `latency_score = 50` and mark `telemetry_partial`.
- Missing cost telemetry: set `cost_score = 50` and mark `telemetry_partial`.
- Missing quality telemetry: do not dispatch unless in strict fallback mode.

Calibration logging:

- Include `telemetry_window_days`, `sample_size`, and `telemetry_partial` in the model selection report when applicable.

```yaml
pseudocode_score_calibration_normalization: |
  # Score Calibration & Normalization - Pseudocode

  # Constants
  MIN_SAMPLE = 20
  CAL_WINDOW_DAYS = 14
  PRIOR_BLEND_WEIGHT = 0.60
  PRIOR_OBS_WEIGHT = 0.40
  RELIABILITY_CLAMP_MIN = 0.85
  RELIABILITY_CLAMP_MAX = 1.05
  NEUTRAL_SCORE = 50

  # Helpers
  function clamp(x, lo, hi):
    return max(lo, min(hi, x))

  function normalize(value, min_x, max_x):
    if max_x == min_x:
      return NEUTRAL_SCORE
    return 100 * (value - min_x) / (max_x - min_x)

  function inverse_normalize(value, min_x, max_x):
    if max_x == min_x:
      return NEUTRAL_SCORE
    return 100 * (max_x - value) / (max_x - min_x)

  function blend_with_prior(observed, prior):
    return PRIOR_BLEND_WEIGHT * prior + PRIOR_OBS_WEIGHT * observed

  # Main routine
  function calibrate_and_normalize(models, telemetry_window_days = CAL_WINDOW_DAYS):
    telemetry_stats = collect_telemetry(models, telemetry_window_days)

    mins_maxs = compute_min_max(telemetry_stats, metrics=[quality_raw, latency_raw, cost_raw], priors=global_priors())

    results = {}
    for model in models:
      stats = telemetry_stats.get(model, {})
      sample_size = stats.sample_size or 0
      telemetry_partial = false

      if sample_size < MIN_SAMPLE:
        observed_quality = stats.quality_raw if exists(stats.quality_raw) else global_priors().quality
        observed_latency = stats.latency_raw if exists(stats.latency_raw) else global_priors().latency
        observed_cost = stats.cost_raw if exists(stats.cost_raw) else global_priors().cost

        quality_value = blend_with_prior(observed_quality, global_priors().quality)
        latency_value = blend_with_prior(observed_latency, global_priors().latency)
        cost_value = blend_with_prior(observed_cost, global_priors().cost)
        telemetry_partial = true
      else:
        quality_value = stats.quality_raw
        latency_value = stats.latency_raw
        cost_value = stats.cost_raw

      if not exists(quality_value):
        quality_score = NEUTRAL_SCORE
        telemetry_partial = true
      else:
        quality_score = normalize(quality_value, mins_maxs.quality.min, mins_maxs.quality.max)

      if not exists(latency_value):
        latency_score = NEUTRAL_SCORE
        telemetry_partial = true
      else:
        latency_score = inverse_normalize(latency_value, mins_maxs.latency.min, mins_maxs.latency.max)

      if not exists(cost_value):
        cost_score = NEUTRAL_SCORE
        telemetry_partial = true
      else:
        cost_score = inverse_normalize(cost_value, mins_maxs.cost.min, mins_maxs.cost.max)

      success_rate = stats.success_rate_30d or global_priors().success_rate
      reliability_factor = clamp(success_rate, RELIABILITY_CLAMP_MIN, RELIABILITY_CLAMP_MAX)

      if stats.hard_failures >= 2:
        eligible = false
      else:
        eligible = true

      selection_score = w_quality * quality_score + w_latency * latency_score + w_cost * cost_score
      final_selection_score = selection_score * reliability_factor

      results[model] = {
        selection_score: selection_score,
        final_selection_score: final_selection_score,
        quality_score: quality_score,
        latency_score: latency_score,
        cost_score: cost_score,
        reliability_factor: reliability_factor,
        telemetry_window_days: telemetry_window_days,
        sample_size: sample_size,
        telemetry_partial: telemetry_partial,
        eligible: eligible
      }

    return results

  # Usage notes: provide weights `w_quality`, `w_latency`, `w_cost` per subagent at selection time.
```

### Adaptive Score-Based Selection

For each eligible model and subagent task, compute:

`selection_score = w_quality * quality_score + w_latency * latency_score + w_cost * cost_score`

Weight profiles by subagent:

| Subagent | `w_quality` | `w_latency` | `w_cost` | Rationale |
|---|---:|---:|---:|---|
| Software Architect | 0.60 | 0.15 | 0.25 | Prioritize reasoning depth and design quality |
| Senior Developer | 0.50 | 0.25 | 0.25 | Balance implementation quality and turnaround speed |
| Code Reviewer | 0.65 | 0.20 | 0.15 | Prioritize correctness, risk detection, and precision |

Selection rules:

- Choose the highest score among eligible models.
- If top two models are within 3 points, prefer lower cost.
- For critical tasks (security, architecture gate, final review), require `capability_tier != economy` unless no other model is available.
- Log selected model and top-2 runner-up scores in behavior logs.

### Strict Deterministic Fallback

When in `strict-deterministic` mode, use fixed priority by task type with fallback:

| Task Type | Priority 1 | Priority 2 | Priority 3 |
|---|---|---|---|
| Architecture/design | `frontier` | `balanced` | `economy` |
| Implementation | `balanced` | `frontier` | `economy` |
| Review/security | `frontier` | `balanced` | `economy` |
| Simple direct response | `economy` | `balanced` | `frontier` |

Deterministic rules:

- Pick the first available model in priority order.
- Do not re-rank within the same tier.
- On model failure, retry once with next priority model.
- Record the fallback reason and selected replacement.

### Model Selection Guardrails

- Do not use `economy` tier for final quality gate if `frontier` or `balanced` is available.
- Do not optimize cost at the expense of contract completeness.
- If selection confidence is low, prefer quality over speed.
- Keep model policy changes small and reversible; log all policy adjustments in runbook entries.

### Task Criticality Classifier

Classify each request before model selection. Criticality sets minimum model tier and fallback policy.

| Criticality | Typical Task Types | Minimum Tier | Fallback Policy |
|---|---|---|---|
| `P0` | Security review, production incident mitigation, final ship gate on high-risk changes | `frontier` | Allow fallback only to `balanced`; block if unavailable |
| `P1` | Architecture decisions, cross-service refactor planning, compliance-sensitive changes | `balanced` | Prefer `frontier`; allow `balanced`; avoid `economy` |
| `P2` | Standard feature implementation, non-critical bug fixes, routine code review | `balanced` | Allow `balanced` to `economy` if quality guardrails pass |
| `P3` | Simple summaries, low-risk documentation, non-binding analysis | `economy` | Allow any tier based on cost and availability |

Classification rules:

- Default to `P2` when classification is ambiguous.
- Elevate to `P0` for any task that includes security risk, data-loss risk, or deployment-blocking decisions.
- Elevate to `P1` for architecture gate tasks and design approvals.
- Downgrade to `P3` only when no code or production-impacting decision is involved.

Enforcement rules:

- Reject model candidates below the minimum tier for the assigned criticality.
- If no candidate meets minimum tier:
  - In strict mode: mark `blocked` and request user override.
  - In adaptive mode: attempt one controlled fallback per policy, then mark `blocked`.
- Always include `criticality` and `minimum_tier_enforced` in the model selection report.

### Mode Control Interface

Support explicit user control phrases for routing mode changes.

Accepted control phrases:

- `force strict for this run`
- `force strict until changed`
- `return to adaptive`
- `adaptive for this run`
- `show model routing mode`
- `approve temporary tier override for this run`
- `approve temporary tier override until changed`
- `clear tier override`

Control behavior:

- `force strict for this run`: Use `strict-deterministic` only for the current orchestration cycle, then revert to prior persistent mode.
- `force strict until changed`: Set persistent mode to `strict-deterministic`.
- `return to adaptive`: Set persistent mode to `adaptive-score-based`.
- `adaptive for this run`: Use `adaptive-score-based` only for the current orchestration cycle, then revert to prior persistent mode.
- `show model routing mode`: Return active mode, persistent mode, and reason for current selection.
- `approve temporary tier override for this run`: Allow one-time dispatch below enforced minimum tier with explicit risk note.
- `approve temporary tier override until changed`: Set persistent override allowing below-minimum tier dispatches with risk notes.
- `clear tier override`: Remove persistent override and restore normal criticality enforcement.

State and logging requirements:

- Track both `persistent_mode` and `effective_mode` for each cycle.
- Include mode source in output (`default`, `user-override`, `fallback-on-failure`).
- Log mode changes and overrides in behavior/context logs with timestamp and reason.

### Mode State Persistence (Production Rule)

Use one canonical state record so routing mode is deterministic across cycles.

- Canonical store: `.wiki/orchestrator/Runbook.md` latest checkpoint entry.
- Required persisted keys:
  - `persistent_mode`
  - `tier_override_scope` (`none` | `one-run` | `persistent`)
  - `tier_override_active` (`true` | `false`)
  - `updated_at_utc`
- Precedence order when values conflict:

 1. Current-request explicit user control phrase
 2. Persisted state from latest runbook checkpoint
 3. Default mode (`adaptive-score-based`)

- `for this run` controls never update persisted mode.
- `until changed` controls must update persisted mode and create a runbook checkpoint line with reason.

### Blocked Decision Escalation Policy

If model selection is blocked due to minimum tier constraints or unavailable eligible models, follow this escalation flow.

Escalation steps:

1. Re-run discovery once to refresh availability and telemetry.
2. Retry selection once using the same criticality and policy mode.
3. If still blocked, return a `blocked` status with:

- `criticality`
- `minimum_tier_enforced`
- top unavailable/ineligible candidates and reason
- recommended override phrase (if safe)

4. Wait for user decision before proceeding.

Auto-retry guardrails:

- Maximum one discovery refresh and one reselection attempt per blocked event.
- Do not silently downgrade below minimum tier.
- Do not auto-retry if failure reason is policy hard-stop (`P0` tier not available).

Override policy:

- Tier overrides require explicit user phrase.
- `P0` tasks cannot be overridden to `economy` tier.
- Any override must append a visible risk note in both dispatch output and behavior log.
- Override scope must be explicit: one-run or persistent.

Escalation output snippet:

```text
Escalation Status
- status: blocked
- reason: no eligible model meeting minimum tier
- criticality: <P0|P1|P2|P3>
- minimum_tier_enforced: <frontier|balanced|economy>
- retry_attempts: discovery_refresh=1, reselection=1
- safe_override_option: <approve temporary tier override for this run>
- risk_note: <short impact statement>
```

### Dispatch Model Selection Template

For each dispatched subagent, include a compact model selection report before task execution.

Required fields:

- `subagent`
- `task_type`
- `criticality`
- `minimum_tier_enforced`
- `effective_mode`
- `mode_source`
- `selected_model`
- `selection_reason`
- `score_weights` (adaptive mode only)
- `top_candidates` (up to 3 with score or priority order)
- `hard_constraints_checked`
- `fallback_used` (`yes`/`no`)
- `telemetry_window_days` (include when telemetry is partial or calibration window is non-standard)
- `sample_size` (include when below high-confidence threshold of 20 tasks)
- `telemetry_partial` (flag as `true` when latency or cost telemetry is missing)

Output template:

```text
Model Selection Report
- subagent: <Software Architect|Senior Developer|Code Reviewer>
- task_type: <architecture|implementation|review|direct>
- criticality: <P0|P1|P2|P3>
- minimum_tier_enforced: <frontier|balanced|economy>
- effective_mode: <adaptive-score-based|strict-deterministic>
- mode_source: <default|user-override|fallback-on-failure>
- selected_model: <model_id>
- selection_reason: <short reason>
- score_weights: <quality=X, latency=Y, cost=Z>   # adaptive only
- top_candidates:
 - <model_a>: <score or priority_rank>
 - <model_b>: <score or priority_rank>
 - <model_c>: <score or priority_rank>
- hard_constraints_checked: <tool-calling, context-window, reliability>
- fallback_used: <yes|no>
```

Template usage rules:

- Always emit this report for each dispatch.
- If strict mode is active, replace numeric scores with deterministic priority rank.
- If fallback occurs, append one line: `fallback_reason: <reason>`.
- Keep report concise; maximum 14 lines per subagent.

### Per-Subagent Model Override and Precedence

Support explicit per-subagent model assignment when dispatching subagents, with a deterministic precedence chain so behavior is predictable and auditable. Precedence (highest → lowest):

1. `subagent_assigned_model` — explicit `model` parameter passed in the subagent spawn payload.
2. `parent_selected_model` — the `selected_model` chosen by the parent/orchestrator for this task or cycle.
3. `cycle_selected_model` — the orchestrator's cycle-level default model (if set for the current orchestration pass).
4. `global_default_model` — system-wide fallback model configured in persistent state.

Behavioral rules:

- If a `model` is supplied in the subagent spawn call, the subagent must run with that model unless the model is unavailable or violates hard policy (minimum tier, missing capabilities). In that case, fall back to `parent_selected_model` and record `fallback_reason`.
- If no `model` is supplied, the subagent inherits `parent_selected_model` by default.
- If neither `subagent_assigned_model` nor `parent_selected_model` exist, use `cycle_selected_model` then `global_default_model`.
- Always emit the `Model Selection Report` for the subagent showing which precedence branch was used and any fallback reason.

Recommended spawn payload example (for orchestrator to call `runSubagent` or equivalent):

```json
{
 "subagent": "Senior Developer",
 "task": "implement feature X",
 "criticality": "P2",
 "model": "gpt-5-mini",             // optional explicit override
 "context": { ... }
}
```

Precedence pseudocode (orchestrator side):

```pseudo
function resolveModelForSubagent(spawnPayload, parentContext) {
 if (spawnPayload.model && isAllowed(spawnPayload.model)) {
  return { model: spawnPayload.model, source: 'subagent_assigned_model' }
 }
 if (parentContext.selected_model && isAllowed(parentContext.selected_model)) {
  return { model: parentContext.selected_model, source: 'parent_selected_model' }
 }
 if (parentContext.cycle_selected_model && isAllowed(parentContext.cycle_selected_model)) {
  return { model: parentContext.cycle_selected_model, source: 'cycle_selected_model' }
 }
 return { model: global_default_model, source: 'global_default_model' }
}
```

Audit and logging:

- Log the resolved model and `model_source` in the behavior logs and in the `Model Selection Report` emitted to the subagent input.
- If a requested `model` is not available or violates hard constraints, include `fallback_used: yes` and `fallback_reason` in the report.
- Keep the emitted report concise (max 14 lines) and machine-parseable where possible.

Implementation notes:

- Add an optional `model` parameter to the `runSubagent`/spawn API. If the platform tooling cannot be changed, include `model` in the `spawn` `context` field as a temporary measure.
- Ensure the orchestrator performs `isAllowed()` checks: existence in catalog, capability_tier, required tool support, and criticality enforcement before accepting an override.
- Update tests to verify: explicit override honored; override blocked by policy falls back to parent; no override inherits parent; missing parent uses cycle/global default.

### Model Selection Report Examples

Use these examples as reference outputs.

Software Architect (adaptive, architecture task):

```text
Model Selection Report
- subagent: Software Architect
- task_type: architecture
- criticality: P1
- minimum_tier_enforced: balanced
- effective_mode: adaptive-score-based
- mode_source: default
- selected_model: gpt-5.3-codex
- selection_reason: highest final score with strong architecture quality
- score_weights: quality=0.60, latency=0.15, cost=0.25
- top_candidates:
 - gpt-5.3-codex: 92.4
 - claude-sonnet: 90.8
 - gpt-5-mini: 87.1
- hard_constraints_checked: tool-calling, context-window, reliability
- fallback_used: no
```

Senior Developer (adaptive, implementation task):

```text
Model Selection Report
- subagent: Senior Developer
- task_type: implementation
- criticality: P2
- minimum_tier_enforced: balanced
- effective_mode: adaptive-score-based
- mode_source: default
- selected_model: gpt-5-mini
- selection_reason: best quality/latency/cost balance for implementation scope
- score_weights: quality=0.50, latency=0.25, cost=0.25
- top_candidates:
 - gpt-5-mini: 89.6
 - gpt-5.3-codex: 89.2
 - claude-sonnet: 87.5
- hard_constraints_checked: tool-calling, context-window, reliability
- fallback_used: no
```

Code Reviewer (strict, fallback in effect):

```text
Model Selection Report
- subagent: Code Reviewer
- task_type: review
- criticality: P2
- minimum_tier_enforced: balanced
- effective_mode: strict-deterministic
- mode_source: fallback-on-failure
- selected_model: claude-sonnet
- selection_reason: primary frontier model unavailable, next priority selected
- top_candidates:
 - gpt-5.3-codex: priority_rank=1 (unavailable)
 - claude-sonnet: priority_rank=2 (selected)
 - gpt-5-mini: priority_rank=3
- hard_constraints_checked: tool-calling, context-window, reliability
- fallback_used: yes
- fallback_reason: provider timeout on priority_rank=1
```

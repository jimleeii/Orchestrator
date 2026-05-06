---
title: "Runtime Budget Controls"
---

Purpose
- Define runtime limits and behaviors to prevent runaway orchestration, infinite recursion, or uncontrolled parallelism.

Recommended Defaults (tunable)

```yaml
orchestrator_runtime:
  # Maximum nested dispatch depth (how many times the orchestrator may recursively dispatch)
  max_dispatch_depth: 3

  # Maximum retry attempts for a failed subagent task before escalation/block
  max_retries: 1

  # Maximum number of agents dispatched in parallel for a single user request
  max_parallel_agents: 2

  # Maximum allowed growth of conversational/contextual state (approx. characters)
  max_context_growth_chars: 20000

  # Minimum cooldown between dispatch waves (seconds)
  dispatch_cooldown_seconds: 2

  # Absolute cap on concurrently active agents in a session (safety cap)
  max_total_active_agents: 10
```

Behavior When Limits Are Hit
- If `max_dispatch_depth` is exceeded: stop further dispatching and mark the workflow `blocked` with a clear reason and suggested user actions.
- If `max_retries` is exceeded for a subagent: escalate to human operator or surface explicit `blocked` status depending on criticality.
- If `max_parallel_agents` would be exceeded: queue lower-priority tracks or degrade to sequential execution.
- If `max_context_growth_chars` is reached: trim least-recent, low-salience context items and log the trimming action; if trimming is insufficient, mark as `blocked` and request user guidance.
- If any absolute cap (`max_total_active_agents`) is reached: refuse new dispatches until active agents complete; surface a wait/queue message.

Overrides and Audit
- Overrides require explicit user confirmation and must be logged with reason, approver identity, and timestamp.
- All limit-trigger events must be logged to `Behavior-Log.md` with evidence and mitigation steps.

Testing and Acceptance
- Add acceptance tests that simulate deep dispatch recursion, repeated failures, and heavy parallelism to validate enforcement and logging.



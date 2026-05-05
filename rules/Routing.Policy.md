## Routing Policy

Purpose: Centralize the Orchestrator routing rules so changes do not require editing the core runtime.

Key rules:

- Classify requests into `direct`, `single-agent`, or `multi-agent` before dispatch.
- Use `dispatching-parallel-agents` when 2+ independent tracks can run in parallel.
- Limit domain skills to at most 2 per dispatched task unless explicitly requested.
- Retry and escalation:
  - Re-run discovery once on a blocked selection.
  - Retry selection once; if still blocked, produce `blocked` with recommended override.
- Respect `max_orchestration_cycles` (default 3) to avoid infinite loops.

Storage: Keep routing mode state in `.wiki/orchestrator/Runbook.md` as checkpointed entries.

Change process: Small routing updates should be applied here and validated with 2 sample tasks.

```yaml
pseudocode_routing_classification: |
  # Pseudocode: Classify incoming user request for dispatch path

  function classify_request(request):
    # Quick checks that force 'direct'
    if is_trivial_request(request) and no_external_dependencies(request):
      return 'direct'

    # Detect architecture-level or cross-service design needs
    if mentions_system_design(request) or requires_new_components(request):
      return 'multi-agent'  # Architect + Dev + Review

    # Detect single-subsystem implementation tasks
    if is_feature_request(request) and scope_is_single_service(request) and not high_risk(request):
      return 'single-agent'

    # Detect parallelizable independent tracks
    if has_independent_subtasks(request):
      return 'multi-agent'  # with dispatching-parallel-agents skill

    # Default safe path
    return 'single-agent'

  # Usage: call classify_request during intake to choose dispatch path.
```

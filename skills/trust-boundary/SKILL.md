---
name: trust-boundary
description: "Trust boundaries for orchestrator runtime, tool invocation, and subagent delegation."
---

# Trust Boundary
Purpose: define safe delegation and script/tool execution boundaries.
This skill is a concise operational summary of `../../rules/Trust.Boundary.md`.

## Trust Boundaries
Evaluate each request across four trust zones:

1. **Orchestrator**: routing and final policy decisions.
2. **Hooks/runtime**: lifecycle hooks and logging execution.
3. **Subagents**: delegated work under orchestrator constraints.
4. **External**: tools, scripts, filesystems, and external systems.

## Subagent Delegation Boundaries
Do not delegate decisions that must remain centralized:

- Final policy overrides
- Criticality waivers without explicit user approval
- Trust-mode changes (`strict`/`permissive`)

Delegation is allowed for bounded tasks only when all validations pass:

- Validate contract completeness before accepting output.
- Validate safety constraints before delegated tool/script execution.
- Validate output scope and declared side effects.

## Tool Invocation Guardrails
Allow only normalized script paths under:

- `skills/`
- `scripts/`
- `test-scripts/`

Block or escalate these risky patterns:

- Path traversal attempts (`..` escaping allowlist)
- Absolute paths outside repository root
- User home, temp, or system directories
- Symlink escapes beyond allowlisted roots

## Verification Gates

Require human confirmation before delegation when any condition is true:

- Security-sensitive work with unclear blast radius
- Data-loss or irreversible change potential
- Production-impacting schema or deployment decisions
- Policy conflict where minimum tier cannot be met

For non-blocking tasks, enforce machine gates:

- Hard constraints checked (capabilities, context, reliability)
- Scope parity checked (requested vs produced)
- Audit fields recorded (who/why/what changed)

## State and Side Effects

Every delegated action must declare expected state changes:

- Files expected to change
- Execution mode (`read-only`, `controlled-write`)
- External calls required (if any)

After execution, compare expected vs observed effects:

- If mismatched, mark cycle as risk-elevated.
- Require explicit reconciliation note before continuing.

## Delegation Decision Pseudocode

```yaml
pseudocode_trust_boundary_decision: |
  function can_delegate(task, context):
    if task.requires_final_policy_override:
      return {allowed: false, reason: 'orchestrator-only decision'}
    if task.is_security_sensitive or task.has_data_loss_risk:
      return {allowed: false, reason: 'requires human verification gate'}
    if task.requires_tool_invocation:
      if not is_allowed_script_path(task.script_path):
        return {allowed: false, reason: 'script path outside trust boundary'}
      if context.trust_mode == 'strict-no-symlinks' and is_symlink_escape(task.script_path):
        return {allowed: false, reason: 'symlink escape risk'}
    return {allowed: true, reason: 'bounded and validated delegation'}
```

Example scenarios:

- Architecture design proposal → delegation allowed after contract validation.
- Database schema change in production path → blocked pending human review.

## Related References

- Authoritative policy: `../../rules/Trust.Boundary.md`
- Validation pattern: `../contract-validator/SKILL.md`
- Dispatch/intake gate: `../workflow-policy/SKILL.md`



---
name: quality-policy
description: "Expectations for code quality, testing, and review gates applied across the workspace."
---

Quality.Policy Skill

Captures expectations for code quality, tests, and review gates.

## Quality Policy

Principles:

- Every change must have a clear acceptance criterion.
- Tests should be added for logic-level behavior and high-risk changes.
- Code reviewers must validate architecture constraints, security considerations, and complexity trade-offs.

## Required Evidence Schema (Mandatory)

Any claim of `implemented` or `verified` MUST include all fields below:

- `claim_status` (`proposed | implemented | verified | deprecated`)
- `cycle_id`
- `evidence_type` (`test | lint | review | runtime-check | benchmark | manual-validation`)
- `artifact_path`
- `timestamp` (UTC preferred)
- `result` (`pass | fail`)

If any required field is missing, the claim is non-compliant and MUST be downgraded to `proposed`.

## Acceptance Gate (Pass/Fail)

A response passes quality gate only when ALL are true:

1. Contract checklist for the subagent role is complete.
2. Required evidence schema is present for all completion claims.
3. No unresolved blocker-level risks remain.
4. Verification artifacts are traceable to files or logs in workspace/wiki paths.

If one or more checks fail, return `status: partial` with explicit remediation actions.

## Subagent Contract Checklists

### Software Architect

- [ ] Problem framing includes scope, constraints, and non-goals.
- [ ] At least two viable options with explicit trade-offs.
- [ ] Recommended decision with rationale and reversibility notes.
- [ ] Boundaries/interfaces are defined (components, modules, service seams).
- [ ] Risk register includes mitigations and residual risk.
- [ ] Validation strategy defines how success is measured.

### Senior Developer

- [ ] Implementation summary maps to approved architecture.
- [ ] Files/components changed (or explicit read-only plan).
- [ ] Test evidence includes pass/fail and known coverage gaps.
- [ ] Error handling, rollback, and guardrails are documented.
- [ ] Limitations and follow-up items are explicit.
- [ ] Comment/region compliance is stated for changed `.cs` files.

### Code Reviewer

- [ ] Findings are categorized by severity (`critical | high | medium | low`).
- [ ] Each critical/high issue includes actionable remediation.
- [ ] Contract and evidence schema compliance are verified.
- [ ] Approval decision is explicit (`approve | approve-with-conditions | reject`).
- [ ] Residual risks and deferred items are documented.

Review checklist (short):

- [ ] Acceptance criteria present and testable.
- [ ] Unit tests added for new logic and edge cases.
- [ ] No high-cyclomatic complexity functions without refactor.
- [ ] No TODOs left without a plan in `Learning-Backlog.md`.

## Ownership

`skills/quality-policy/SKILL.md` is the canonical owner for acceptance criteria and output contract enforcement.
Other files may summarize quality expectations but MUST defer to this file for pass/fail gates.

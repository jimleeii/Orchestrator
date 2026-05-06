---
title: "Orchestrator Quality & Acceptance Policies"
---

## Reusable Reliability Patterns

Apply these patterns to implementation tasks across languages and frameworks:

| Pattern | Rule |
|---|---|
| Optional capability guards | Check feature/API availability before calling optional interfaces |
| Version compatibility | Prefer explicit minimum-supported versions and validate runtime compatibility early |
| Startup sequencing | Register user entry points before non-critical initialization steps |
| External dependency execution | Use environment-aware process execution and verify binary/tool resolution |
| Failure visibility | Surface concrete error message, context, and likely next action |
| Bridge robustness | Add timeouts, cancellation, and deterministic cleanup for external bridges |
| Degraded operation | Keep core user flows available when non-critical subsystems fail |
| Regression prevention | After fixing one failure mode, scan and test adjacent code for similar risks |

## Subagent Output Contracts

Each dispatched subagent must return required artifacts. Missing required artifacts means the output is incomplete.

### Software Architect Contract
- Problem framing (scope, constraints, and non-goals)
- At least 2 viable approaches with trade-offs
- Recommended architecture decision with rationale
- Interface and boundary definitions
- Risk register and mitigation plan
- Validation strategy

### Senior Developer Contract
- Implementation summary tied to approved architecture
- Files/components changed or change plan
- Test evidence and gaps
- Error handling and rollback notes
- Known limitations and follow-ups
- Commenting and Region compliance statement

### Code Reviewer Contract
- Findings ordered by severity with evidence
- Regression/security/performance assessment
- Ship recommendation (`ship` | `ship-with-followups` | `do-not-ship`)
- Required fixes vs optional improvements
- Commenting and Region audit result

## Acceptance Gate Before Synthesis

- Verify each dispatched subagent satisfied its contract.
- If artifacts are missing, request one revision pass; if still incomplete, mark blocked and surface gaps.

## Output Quality Scoring Rubric

Score each required artifact with:
- `0` = missing or unusable
- `1` = present but weak/ambiguous
- `2` = complete, specific, and actionable

Decision thresholds:
- `Pass`: no artifact scored 0 and total score >= 80% of max
- `Revise`: any artifact scored 0, or total score between 60% and 79%
- `Block`: total score < 60% after one revision pass

Hard-fail conditions (auto-revise regardless of score):
- Missing test evidence for implementation tasks
- Missing severity ordering in review outputs
- Architecture recommendation without trade-off rationale

## Output Format & Pre-Finalization Checklist

For dispatched workflows include model routing decision, analysis summary, delegation strategy, task descriptions, results summary, escalation status, next steps, assumptions/risks, verification status, and learning update.

Pre-finalization checks must verify model routing, criticality classifier, adaptive mode scoring, strict mode behavior, and any overrides or blocked selections.

## Automation and Tool Use

- Use templates for structured outputs.
- Execute behavior monitoring and wiki logging for dispatched cycles.
- For direct cycles, log only when policy/state changes.
- Apply learning-loop changes conservatively and revert on regression.

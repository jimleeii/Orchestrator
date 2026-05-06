---
title: "Policy Precedence & Conflict Resolution"
---

Purpose
- Define a clear precedence order to resolve conflicts between policy files and user instructions.

Policy Precedence (highest → lowest)
1. User instructions
2. Safety constraints
3. Quality gates
4. Workflow policy
5. Routing heuristics
6. Defaults

Guidance
- When two policies conflict, apply the higher-precedence rule.
- If user instructions conflict with policies, surface the conflict and require explicit user confirmation to override safety or quality gates.
- Document overrides with reason, approver (user or operator), and timestamp.
- Provide tie-break examples and test cases in the rules' unit tests or acceptance checks.

Example
- If `Workflow.Policy` requests an automated dispatch but `Routing.Policy` forbids remote execution, follow `Workflow.Policy` only if it is subordinate to a user instruction that explicitly authorizes the override; otherwise follow the higher-precedence routing constraint and surface a block.

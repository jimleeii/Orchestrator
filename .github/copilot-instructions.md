---
title: Copilot workspace instructions
---

# Workspace AI policies

Purpose: always-on guidance for AI coding agents operating in this repository. See the companion [AGENTS.md](../AGENTS.md) for entrypoints.

## Quick rules
- Keep PRs small and focused; prefer multiple incremental PRs over a single large refactor.
- Include failing test output and exact commands to reproduce any CI failures in PR descriptions.

## Commit & PR messages
- Use concise prefixes: `Fix:`, `Feat:`, `Chore:` and reference issue IDs when available.

## RTK Rule

Always prefix shell commands with `rtk`. For example, use `rtk dotnet build` instead of `dotnet build` to ensure the command runs in the correct environment with necessary context. For PowerShell scripts, use `rtk pwsh` to execute the script with the appropriate runtime context.

> Rule: Use `rtk` before shell commands so output stays compact and token-efficient.

```bash
# Instead of:              Use:
git status                 rtk git status
git log -10                rtk git log -10
cargo test                 rtk cargo test
docker ps                  rtk docker ps
kubectl get pods           rtk kubectl pods
pwsh                       rtk pwsh
```

## Meta commands

```bash
rtk gain              # Token savings dashboard
rtk gain --history    # Per-command savings history
rtk discover          # Find missed rtk opportunities
rtk proxy <cmd>       # Run raw (no filtering) but track usage
```

## When to ask for human review
- Large API or public-surface changes
- Modifying project GUIDs, package IDs, or deployment manifests

## Planning
- Use doc/superpowers/plans/ for multi-step plans or design docs.

## Behavior Logging (When Orchestrator is active)
- Use .wiki/orchestrator/Behavior-Patterns.md to document common patterns and heuristics for orchestrator behavior.
- Use .wiki/orchestrator/Runbook.md for operational steps and maintenance tasks related to the orchestrator.
- Use .wiki/orchestrator/Home.md as the single source of truth for orchestrator-level guidance, linking to key documents and logs.
- Use .wiki/orchestrator/Project-Context-Log.md can be used to maintain an evolving log of project context and insights for the orchestrator.
- Use .wiki/orchestrator/Behavior-Logs/ for detailed logs of orchestrator behavior and decision-making during complex operations.
- Use .wiki/orchestrator/Learning-Logs/ for logs of learning and decision-making during complex operations.
- Use .wiki/orchestrator/Skill-Usage-Logs/ for logs of skill usage and performance during complex operations.

## Workspace guidance

- `AGENTS.md` and `CLAUDE.md` are the full, authoritative workspace guide for this Orchestrator repo.
- Keep edits surgical and consistent with the existing `rules/`, `prompts/`, `scripts/`, and `skills/` layout.

## Links
- Workspace summary: [AGENTS.md](../AGENTS.md)
- CLAUDE reference: [CLAUDE.md](../CLAUDE.md)

---
<!-- End workspace instructions -->
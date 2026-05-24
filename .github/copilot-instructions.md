# RTK — Token-Optimized CLI

Use `rtk` before shell commands so output stays compact and token-efficient.

```bash
# Instead of:              Use:
git status                 rtk git status
git log -10                rtk git log -10
cargo test                 rtk cargo test
docker ps                  rtk docker ps
kubectl get pods           rtk kubectl pods
pwsh                       rtk pwsh
```

## Workspace guidance

- `AGENTS.md` and `CLAUDE.md` are the full, authoritative workspace guide for this Orchestrator repo.
- Keep edits surgical and consistent with the existing `rules/`, `prompts/`, `scripts/`, and `skills/` layout.

## Meta commands

```bash
rtk gain              # Token savings dashboard
rtk gain --history    # Per-command savings history
rtk discover          # Find missed rtk opportunities
rtk proxy <cmd>       # Run raw (no filtering) but track usage
```

## Logging Policy

Purpose: Reduce logging overhead for small tasks while retaining auditability for complex workflows.

Levels:

- `minimal`: used for direct/simple responses — no behavior wiki appends or skill-usage records
- `compact`: single-agent cycles — one-line behavior checkpoint plus a `Skill-Usage-Log.md` entry derived from prompt/output parsing
- `full`: multi-agent cycles, concurrent cycles, failures, or policy changes — full behavior, skill-usage, and context logs plus transcript artifacts with parsed skills

Dispatch path to level mapping:

| Dispatch Path | Default Level | Notes |
|---|---|---|
| `direct` | `minimal` | Direct responses, triage, or policy explanation only |
| `single-agent` | `compact` | Single subagent execution; records behavior + skill usage |
| `multi-agent` | `full` | Sequential multi-subagent execution; always full logs |
| `concurrent` | `full` | Parallel subagent execution; always full logs for aggregation visibility |

Rules:

- All dispatch paths respect event flags (`failure_detected`, `persistent_mode_change`, `tier_override`) which upgrade to `full`.
- `force_persist_all` is a strict override: when `true`, **all** cycles return `full` regardless of dispatch path or event flags.
- On any persistent mode change or tier override, always use `full` for the cycle that caused the change.
- Keep behavior log entries compact; prefer checklist-style bullets and links to artifacts.
- Skill usage is recorded by parsing Copilot Chat input/output and explicit runtime invocation hints. The external `%USERPROFILE%\.copilot\skills` folder is read-only metadata, not the source of truth for runtime logging.
- Persisted logging: compact and full cycles write `Behavior-Log.md` plus `Skill-Usage-Log.md` entries to `.wiki/orchestrator/`; full cycles additionally write transcripts, attachments, screenshots, and policy-change records.

Configuration:

- `force_persist_all` (boolean, strict override): When `true`, override the logging level decision and treat every orchestration cycle as `full`, persisting artifacts to `.wiki/orchestrator/`. This is a strict override: it takes precedence over all dispatch paths and event flags. Default: `false`.

Change process: Logging level changes are small, reversible edits to this file and should be noted in `.wiki/orchestrator/Runbook.md`. Skill-usage records should be parsed from Copilot Chat input/output plus explicit runtime invocation hints, then written alongside the cycle logs under `.wiki/orchestrator/`.

```yaml
pseudocode_choose_logging_level: |
	# Pseudocode: Determine logging verbosity for an orchestration cycle
	# STRICT OVERRIDE: force_persist_all always returns 'full'
	
	function choose_logging_level(dispatch_path, event_flags, config):
		# Strict override: force_persist_all takes precedence over all other rules
		if config.get('force_persist_all'):
			return 'full'
		
		# Event flags escalate to full regardless of dispatch path
		# event_flags may include: persistent_mode_change, tier_override, failure_detected
		if event_flags.persistent_mode_change or event_flags.tier_override:
			return 'full'
		if event_flags.failure_detected:
			return 'full'
		
		# Dispatch path determines level when no overrides
		if dispatch_path in ('multi-agent', 'concurrent'):
			return 'full'
		if dispatch_path == 'single-agent':
			return 'compact'
		
		# Default for direct or unknown paths
		return 'minimal'

	# Usage: call choose_logging_level before starting cycle and ensure behavior, skill-usage, and transcript artifacts are persisted per level.
	# Contract: force_persist_all is a strict override and MUST be honored in both hooks.log_hooks and src.orchestrator_runtime.
```

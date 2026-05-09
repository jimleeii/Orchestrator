Post-hook integration for Copilot Chat
===================================

This document explains how to capture a Copilot Chat conversation transcript and pass it to the Orchestrator post-hook so behavior, skills used, learning notes, and context are persisted to the `.wiki/orchestrator/` logs.

Quick summary
-------------

- Use `scripts/post_chat_hook.py` from your chat runtime or extension to pipe the transcript and metadata.
- The post-hook will call `scripts/log_hook_runner.py --phase post` which invokes `hooks.log_hooks.log_cycle()` to perform the actual persistence.

Examples
--------

Write a transcript file and call the helper:

```powershell
Set-Content -Path .wiki\orchestrator\transcripts\session-20260509.md -Value $transcript
python scripts/post_chat_hook.py --transcript-file ".wiki/orchestrator/transcripts/session-20260509.md" --summary "Copilot chat session end" --skills "prompt-optimizer,contract-validator" --author "alice" --force-persist
```

Pipe transcript from stdin:

```powershell
Get-Content chat.raw | python scripts/post_chat_hook.py --summary "Chat end" --skills "prompt-optimizer" --author "alice" --force-persist
```

Event flags and structured metadata
----------------------------------

You can include additional structured event flags (JSON) that will be merged into the `event_flags` map passed to `log_cycle()`.

```powershell
python scripts/post_chat_hook.py --summary "Chat end" --event-flags '{"failure_detected": true, "tier_override": false}' --force-persist
```

Or pass an event file directly to the runner:

```powershell
python scripts/log_hook_runner.py --phase post --summary "Chat end" --event-flags-file scripts/chat_event_flags.json --force-persist
```

Notes
-----

- `log_hook_runner.py` supports `--skills`, `--tags`, `--author`, `--dispatch-path`, `--transcript-file`, `--event-flags` (JSON string) and `--event-flags-file`.
- If your Copilot Chat environment cannot write files, implement a small connector that posts transcript text to a local runner which then calls `scripts/post_chat_hook.py`.

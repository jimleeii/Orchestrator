#!/usr/bin/env python3
"""Run `hooks.log_hooks.log_cycle` from hook runner JSON configs.

This small CLI is intended to be invoked by repository hook runners
(e.g. `.github/hooks/*.json`) as a command. It maps a few simple
arguments to `log_cycle()` so hooks can persist logs at pre/mid/post
phases without shelling out to the markdown CLI directly.
"""
from __future__ import annotations

import argparse
import sys
import json
from pathlib import Path
from typing import Optional


def find_repo_root(start: Optional[Path] = None) -> Path:
    p = Path(start or __file__).resolve()
    cur = p if p.is_dir() else p.parent
    markers = (".wiki/orchestrator", "orchestrator.agent.md", ".git")
    for _ in range(20):
        for m in markers:
            if (cur / m).exists():
                return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run orchestrator log hook runner.")
    parser.add_argument("--phase", choices=["pre", "mid", "post"], default="pre", help="Hook phase")
    parser.add_argument("--dispatch-path", default="direct", help="Dispatch path (direct/single-agent/multi-agent)")
    parser.add_argument("--summary", default="", help="Short summary message")
    parser.add_argument("--skills", help="Comma-separated skills list", default=None)
    parser.add_argument("--transcript-file", help="Path to transcript file to include", default=None)
    parser.add_argument("--author", help="Author name", default=None)
    parser.add_argument("--preview", action="store_true", help="Run in preview mode (no writes)")
    parser.add_argument("--force-persist", action="store_true", help="Force full persist")
    parser.add_argument("--tags", help="Comma-separated tags", default=None)
    parser.add_argument("--event-flags", help="JSON string of event flags (e.g. '{\"failure_detected\": true}')", default=None)
    parser.add_argument("--event-flags-file", help="Path to a JSON file containing event flags", default=None)
    parser.add_argument("--prompt-command", help="Optional prompt command to run (e.g. /runbook)", default=None)
    parser.add_argument("--root", help="Repository root (for testing)", default=None)
    args = parser.parse_args()

    repo_root = Path(args.root) if args.root else find_repo_root(Path(__file__))
    # Ensure repo root is on sys.path so `hooks` can be imported reliably
    sys.path.insert(0, str(repo_root))

    try:
        from hooks.log_hooks import log_cycle
    except Exception as e:  # pragma: no cover - import/runtime guard
        print("Failed to import hooks.log_hooks:", e, file=sys.stderr)
        return 2

    skills = [s for s in (args.skills.split(",") if args.skills else []) if s]
    transcript = None
    if args.transcript_file:
        tf = Path(args.transcript_file)
        if tf.exists():
            transcript = tf.read_text(encoding="utf-8")
        else:
            print(f"Transcript file not found: {tf}", file=sys.stderr)

    # Base event flags always include the hook phase. Additional flags can be supplied
    # via `--event-flags` (JSON string) or `--event-flags-file` (JSON file).
    event_flags = {"hook_phase": args.phase}
    if args.event_flags:
        try:
            parsed = json.loads(args.event_flags)
            if isinstance(parsed, dict):
                event_flags.update(parsed)
        except Exception as e:  # pragma: no cover - user input parsing
            print("Failed to parse --event-flags JSON:", e, file=sys.stderr)
            return 4
    if args.event_flags_file:
        try:
            p = Path(args.event_flags_file)
            if p.exists():
                parsed = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(parsed, dict):
                    event_flags.update(parsed)
            else:
                print(f"Event flags file not found: {p}", file=sys.stderr)
        except Exception as e:  # pragma: no cover - user input parsing
            print("Failed to read/parse --event-flags-file:", e, file=sys.stderr)
            return 5

    try:
        res = log_cycle(
            dispatch_path=args.dispatch_path,
            event_flags=event_flags,
            summary=args.summary,
            skills=skills or None,
            transcript=transcript,
            force_persist_all=bool(args.force_persist),
            author=args.author,
            root=repo_root,
            target_root=None,
            tags=args.tags,
            preview=args.preview,
            prompt_command=args.prompt_command,
        )
    except Exception as e:  # pragma: no cover - runtime exception reporting
        print("log_cycle raised an exception:", e, file=sys.stderr)
        return 3

    # Print a compact result for hook runner visibility
    print(res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

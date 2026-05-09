#!/usr/bin/env python3
"""Helper to capture a Copilot chat transcript and invoke the post-hook persist step.

This script accepts a transcript (file or stdin), optional metadata (skills, tags,
author, dispatch path), writes a temporary transcript file if needed and calls
`scripts/log_hook_runner.py --phase post` to persist logs.

Example:
  echo "conversation text" | python scripts/post_chat_hook.py --summary "Chat end" --skills "prompt-optimizer,contract-validator" --author "alice"

Or with an existing transcript file:
  python scripts/post_chat_hook.py --transcript-file ".wiki/orchestrator/transcripts/session-20260509.md" --summary "Chat end" --skills "..."
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture chat transcript and call post-hook to persist logs.")
    parser.add_argument("--transcript-file", help="Path to existing transcript file (optional)")
    parser.add_argument("--summary", help="Short summary for the log entry", default="Chat session end")
    parser.add_argument("--skills", help="Comma-separated skills list", default=None)
    parser.add_argument("--author", help="Author name", default=None)
    parser.add_argument("--tags", help="Comma-separated tags", default="copilot-chat")
    parser.add_argument("--dispatch-path", help="Dispatch path (direct/single-agent/multi-agent)", default="single-agent")
    parser.add_argument("--event-flags", help="JSON string of event flags to pass through", default=None)
    parser.add_argument("--force-persist", action="store_true", help="Force persistence (adds --force-persist to the runner)")
    parser.add_argument("--prompt-command", help="Optional prompt command to run (e.g. /runbook)", default=None)
    args = parser.parse_args()

    transcript_path: Optional[Path] = None
    # If a transcript file provided, use it. Otherwise read stdin.
    if args.transcript_file:
        t = Path(args.transcript_file)
        if not t.exists():
            print(f"Transcript file not found: {t}", file=sys.stderr)
            return 2
        transcript_path = t
    else:
        if sys.stdin.isatty():
            print("No transcript provided via stdin or --transcript-file", file=sys.stderr)
            return 3
        txt = sys.stdin.read()
        if not txt.strip():
            print("Empty transcript", file=sys.stderr)
            return 4
        # Write a temp file for log_hook_runner to consume
        tf = tempfile.NamedTemporaryFile(prefix="copilot_transcript_", suffix=".md", delete=False)
        tf.write(txt.encode("utf-8"))
        tf.flush()
        tf.close()
        transcript_path = Path(tf.name)

    cmd = [sys.executable, "scripts/log_hook_runner.py", "--phase", "post", "--summary", args.summary]
    if args.skills:
        cmd += ["--skills", args.skills]
    if args.author:
        cmd += ["--author", args.author]
    if args.tags:
        cmd += ["--tags", args.tags]
    if args.dispatch_path:
        cmd += ["--dispatch-path", args.dispatch_path]
    if args.event_flags:
        cmd += ["--event-flags", args.event_flags]
    if args.force_persist:
        cmd += ["--force-persist"]
    if args.prompt_command:
        cmd += ["--prompt-command", args.prompt_command]
    if transcript_path:
        cmd += ["--transcript-file", str(transcript_path)]

    # Run the runner
    try:
        proc = subprocess.run(cmd, check=False)
        return proc.returncode
    finally:
        # If we wrote a temp transcript file, leave it for audit purposes.
        pass


if __name__ == "__main__":
    raise SystemExit(main())

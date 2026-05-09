#!/usr/bin/env python3
"""CLI to append prompt-style log entries to repository template log files.

Usage examples:
  python scripts/log_prompt.py /full-log "Fixed agent routing bug"
  echo "Detailed multi-line message" | python scripts/log_prompt.py /info -a "Wei Li"

The script maps short prompt commands (e.g. `/full-log`, `/info`, `/error`) to
one or more markdown files under the `.wiki/orchestrator/` folder and appends a timestamped
entry.
"""
from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
import textwrap
import re

TEMPLATES_DIR_NAME = ".wiki/orchestrator"

LOG_COMMANDS: Dict[str, List[str]] = {
    "/full-log": [
        "Behavior-Log.md",
        "Behavior-Patterns.md",
        "Learning-Backlog.md",
        "Project-Context-Log.md",
        "Runbook.md",
        "Skill-Usage-Log.md",
    ],
    "/all-log": [
        "Behavior-Log.md",
        "Behavior-Patterns.md",
        "Learning-Backlog.md",
        "Project-Context-Log.md",
        "Runbook.md",
        "Skill-Usage-Log.md",
    ],
    "/critical": ["Behavior-Log.md", "Project-Context-Log.md", "Runbook.md"],
    "/error": ["Behavior-Log.md", "Project-Context-Log.md"],
    "/warning": ["Behavior-Log.md", "Behavior-Patterns.md"],
    "/warn": ["Behavior-Log.md", "Behavior-Patterns.md"],
    "/info": ["Skill-Usage-Log.md", "Behavior-Log.md"],
    "/debug": ["Runbook.md", "Learning-Backlog.md"],
    "/trace": ["Learning-Backlog.md"],
    "/behavior-log": ["Behavior-Log.md"],
    "/behavior": ["Behavior-Log.md"],
    "/patterns-log": ["Behavior-Patterns.md"],
    "/pattern": ["Behavior-Patterns.md"],
    "/learning-backlog": ["Learning-Backlog.md"],
    "/project-context": ["Project-Context-Log.md"],
    "/runbook": ["Runbook.md"],
    "/skill-usage": ["Skill-Usage-Log.md"],
}


def find_repo_root(start: Path | None = None) -> Path:
    p = Path(start or __file__).resolve()
    cur = p if p.is_dir() else p.parent
    markers = (TEMPLATES_DIR_NAME, 'orchestrator.agent.md', '.git')
    for _ in range(20):
        for m in markers:
            if (cur / m).exists():
                return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return Path(__file__).resolve().parents[1]


def get_author(repo_root: Path) -> str:
    try:
        out = subprocess.check_output(["git", "config", "--get", "user.name"], cwd=str(repo_root), stderr=subprocess.DEVNULL)
        name = out.decode().strip()
        if name:
            return name
    except Exception:
        pass
    name = os.environ.get("GIT_AUTHOR_NAME") or os.environ.get("USER") or os.environ.get("USERNAME")
    if name:
        return name
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def format_entry(command: str, author: str, message: str, tags: str | None = None) -> str:
    now = datetime.now(timezone.utc).astimezone()
    timestamp = now.isoformat(timespec="seconds")
    header = f"### {timestamp} — {command} — {author}\n\n"
    if tags:
        header += f"Tags: {tags}\n\n"
    body = message.strip() + "\n\n"
    return header + body


def ensure_file(path: Path):
    if not path.exists():
        path.write_text(f"# {path.name}\n\n", encoding="utf-8")


def _find_prompt_template(repo_root: Path, cmd_name: str) -> str | None:
    """Find an `entry_template` block in prompts/<cmd_name>.prompt.md and return it dedented.

    Returns None if no template is found.
    """
    prompt_path = repo_root / 'prompts' / f"{cmd_name}.prompt.md"
    if not prompt_path.exists():
        return None
    text = prompt_path.read_text(encoding='utf-8')
    # Locate 'entry_template:' and capture the following indented block or until a code fence
    m = re.search(r'entry_template:\s*\|\s*\n', text)
    if not m:
        return None
    start = m.end()
    lines = text[start:].splitlines()
    collected = []
    for line in lines:
        # stop at an unindented code fence marker
        if line.strip().startswith('```'):
            break
        # collect indented lines (or blank lines)
        if line.startswith(' ') or line.startswith('\t') or line.strip() == '':
            collected.append(line)
            continue
        # stop when encountering a non-indented non-blank line
        break
    if not collected:
        return None
    tpl = '\n'.join(collected)
    tpl = textwrap.dedent(tpl)
    return tpl.rstrip('\n')


def _render_template(template: str, message: str, author: str, tags: str | None = None) -> str:
    now = datetime.now(timezone.utc).astimezone()
    date = now.strftime('%Y%m%d')
    time = now.strftime('%H%M%S')
    iso = now.isoformat(timespec='seconds')
    utc = now.astimezone(timezone.utc).replace(microsecond=0).isoformat()

    tpl = template.replace('YYYYMMDD', date).replace('XXX', time)
    lines = tpl.splitlines()
    out_lines: list[str] = []
    inserted_change = False
    for line in lines:
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith('###'):
            out_lines.append(line)
            continue
        if low.startswith('- date:'):
            out_lines.append(f"- Date: {iso}")
            continue
        if low.startswith('- timestamp (utc):'):
            out_lines.append(f"- Timestamp (UTC): {utc}")
            continue
        if 'change applied' in low or low.startswith('- change applied:'):
            # Insert message; preserve multi-line
            if '\n' in message:
                out_lines.append('- Change Applied: |')
                for mline in message.splitlines():
                    out_lines.append('  ' + mline)
            else:
                out_lines.append(f"- Change Applied: {message}")
            inserted_change = True
            continue
        out_lines.append(line)

    if not inserted_change:
        out_lines.append('')
        # add message at end
        out_lines.extend(message.splitlines())

    # Optionally add tags/author if not present in template
    if tags:
        out_lines.append('')
        out_lines.append(f"Tags: {tags}")
    if author:
        out_lines.append('')
        out_lines.append(f"Author: {author}")

    return '\n'.join(out_lines) + '\n\n'


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a prompt-style log entry to repository template log files.")
    parser.add_argument("command", help="Prompt command name (e.g. /full-log, /info)")
    parser.add_argument("message", nargs="?", help="Message text to log. If omitted, read from stdin.")
    parser.add_argument("-a", "--author", help="Author name to include in the entry.")
    parser.add_argument("-t", "--tags", help="Comma-separated tags to add to the entry.")
    parser.add_argument("--preview", action="store_true", help="Print the generated entries but do not write files.")
    parser.add_argument("--root", help="Repository root (for testing). If omitted, discovered automatically.")
    args = parser.parse_args()

    repo_root = Path(args.root) if args.root else find_repo_root(Path(__file__))
    templates_dir = repo_root / TEMPLATES_DIR_NAME

    if not templates_dir.exists():
        print(f"Templates directory not found at {templates_dir}; creating it.")
        templates_dir.mkdir(parents=True, exist_ok=True)

    cmd = args.command.strip()
    if not cmd.startswith("/"):
        cmd = "/" + cmd
    cmd_low = cmd.lower()

    targets = LOG_COMMANDS.get(cmd_low)
    if targets is None:
        print("Unknown command:", cmd)
        print("Available commands:")
        for k in sorted(LOG_COMMANDS.keys()):
            print(" ", k)
        return 2

    msg = args.message
    if not msg:
        if not sys.stdin.isatty():
            msg = sys.stdin.read().strip()
        else:
            print("Enter message (end with Ctrl-D/Ctrl-Z):")
            try:
                msg = sys.stdin.read().strip()
            except KeyboardInterrupt:
                msg = ""
    if not msg:
        print("No message provided; aborting.")
        return 1

    author = args.author or get_author(repo_root)

    entries: Dict[Path, str] = {}
    # Attempt to find a prompt-based entry template for this command in prompts/
    cmd_name = cmd_low.lstrip('/')
    prompt_tpl = _find_prompt_template(repo_root, cmd_name)
    for f in targets:
        path = templates_dir / f
        ensure_file(path)
        if prompt_tpl:
            entry = _render_template(prompt_tpl, msg, author, args.tags)
        else:
            entry = format_entry(cmd, author, msg, args.tags)
        entries[path] = entry

    if args.preview:
        print("--- Preview (no files written) ---")
        for path, entry in entries.items():
            print(f"\n--- {path} ---\n")
            print(entry)
        return 0

    for path, entry in entries.items():
        with path.open("a", encoding="utf-8") as fh:
            fh.write(entry)
    print(f"Wrote entry for {len(entries)} file(s):")
    for p in entries.keys():
        try:
            print(" -", p.relative_to(repo_root))
        except Exception:
            print(" -", str(p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

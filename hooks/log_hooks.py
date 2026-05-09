"""Logging hooks for the Orchestrator.

These helpers follow `rules/Logging.Policy.md` to choose a logging verbosity
(`minimal` | `compact` | `full`) and persist entries by invoking the
`scripts/log_prompt.py` CLI. They also provide a small helper to write
cycle transcripts under `.wiki/orchestrator/transcripts/` when available.

Usage:
  from hooks.log_hooks import log_cycle
  res = log_cycle(
      dispatch_path='single-agent',
      event_flags={'failure_detected': False},
      summary='Completed single-agent task',
      skills=['skillA','skillB'],
      transcript=None,
      force_persist_all=False,
      author='Wei Li',
  )

The implementation intentionally calls the existing `scripts/log_prompt.py`
so the project keeps a single mapping of prompt-commands -> template files.
"""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict

TEMPLATES_DIR_NAME = ".wiki/orchestrator"


def find_repo_root(start: Optional[Path] = None) -> Path:
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


def choose_logging_level(dispatch_path: str, event_flags: Optional[Dict[str, bool]] = None, config: Optional[Dict[str, bool]] = None) -> str:
    """Choose logging level per `rules/Logging.Policy.md` pseudocode.

    dispatch_path: 'direct' | 'single-agent' | 'multi-agent' (or similar)
    event_flags: keys may include: 'persistent_mode_change', 'tier_override', 'failure_detected'
    config: supported keys: 'force_persist_all'

    Returns: 'minimal' | 'compact' | 'full'
    """
    event_flags = event_flags or {}
    config = config or {}
    if config.get('force_persist_all'):
        return 'full'
    if event_flags.get('persistent_mode_change') or event_flags.get('tier_override') or event_flags.get('failure_detected'):
        return 'full'
    if dispatch_path == 'multi-agent':
        return 'full'
    if dispatch_path == 'single-agent':
        return 'compact'
    return 'minimal'


def _run_log_command(repo_root: Path, command: str, message: str, author: Optional[str] = None, tags: Optional[str] = None, preview: bool = False, script_root: Optional[Path] = None):
    script = repo_root / 'scripts' / 'log_prompt.py'
    if not script.exists():
        raise FileNotFoundError(f"log_prompt.py not found at expected location: {script}")
    cmd = [sys.executable, str(script), command, message]
    if author:
        cmd += ['--author', str(author)]
    if tags:
        cmd += ['--tags', str(tags)]
    if script_root:
        cmd += ['--root', str(script_root)]
    if preview:
        cmd += ['--preview']
    # Use run so exceptions propagate to callers for the orchestrator to handle
    return subprocess.run(cmd, check=True)


def write_transcript(repo_root: Path, transcript: str, prefix: str = 'transcript') -> Path:
    transcripts_dir = repo_root / TEMPLATES_DIR_NAME / 'transcripts'
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).astimezone()
    ts = now.strftime('%Y%m%dT%H%M%S%z')
    filename = f"{prefix}-{ts}.md"
    path = transcripts_dir / filename
    header = f"# Transcript {now.isoformat(timespec='seconds')}\n\n"
    path.write_text(header + transcript + "\n", encoding='utf-8')
    return path


def log_cycle(
    dispatch_path: str,
    event_flags: Optional[Dict[str, bool]] = None,
    summary: str = "",
    skills: Optional[List[str]] = None,
    transcript: Optional[str] = None,
    force_persist_all: bool = False,
    author: Optional[str] = None,
    root: Optional[Path] = None,
    target_root: Optional[Path] = None,
    tags: Optional[str] = None,
    preview: bool = False,
    prompt_command: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """High-level orchestrator hook to persist logs according to policy.

    - Decides level via `choose_logging_level`.
    - For `minimal`: performs no persistent writes and returns quickly.
    - For `compact`: invokes `/info` (writes `Skill-Usage-Log.md` and `Behavior-Log.md`).
    - For `full`: invokes `/full-log` (writes across logs) and optionally writes a transcript.

    Returns a dict with keys describing what was done.
    """
    config = {"force_persist_all": bool(force_persist_all)}
    level = choose_logging_level(dispatch_path, event_flags or {}, config)
    repo_root = Path(root) if root else find_repo_root(None)

    if level == 'minimal':
        return {"level": "minimal", "action": "none"}

    # Build a compact message body used for both compact and full
    body = summary or ("(no summary provided)")
    if skills:
        body += "\n\nSkills: " + ", ".join(skills)

    # If a specific prompt command was requested, run it directly.
    if prompt_command:
        proc = _run_log_command(repo_root, prompt_command, body, author=author, tags=tags, preview=preview, script_root=target_root)
        transcript_path = None
        if transcript and not preview:
            transcript_path = write_transcript(repo_root, transcript)
        return {
            "level": level,
            "command": prompt_command,
            "returncode": str(proc.returncode),
            "transcript": str(transcript_path) if transcript_path else None,
        }

    if level == 'compact':
        # single-agent flows: record behavior + skill usage via `/info`
        proc = _run_log_command(repo_root, '/info', body, author=author, tags=tags, preview=preview, script_root=target_root)
        return {"level": "compact", "command": "/info", "returncode": str(proc.returncode)}

    if level == 'full':
        proc = _run_log_command(repo_root, '/full-log', body, author=author, tags=tags, preview=preview, script_root=target_root)
        transcript_path = None
        # Only write transcript when not in preview mode
        if transcript and not preview:
            transcript_path = write_transcript(repo_root, transcript)
        return {
            "level": "full",
            "command": "/full-log",
            "returncode": str(proc.returncode),
            "transcript": str(transcript_path) if transcript_path else None,
        }

    return {"level": level, "action": "unhandled"}


__all__ = ["choose_logging_level", "log_cycle", "write_transcript"]

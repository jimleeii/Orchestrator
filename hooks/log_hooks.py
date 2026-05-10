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

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

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


def _run_log_command(
    repo_root: Path,
    command: str,
    message: str = "",
    author: Optional[str] = None,
    tags: Optional[str] = None,
    preview: bool = False,
    script_root: Optional[Path] = None,
    context: Optional[Dict[str, Any]] = None,
):
    script = repo_root / 'scripts' / 'log_prompt.py'
    if not script.exists():
        raise FileNotFoundError(f"log_prompt.py not found at expected location: {script}")
    payload = json.dumps(context, ensure_ascii=False) if context is not None else message
    cmd = [sys.executable, str(script), command, payload]
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


def _build_log_context(
    dispatch_path: str,
    event_flags: Optional[Dict[str, bool]] = None,
    summary: str = "",
    skills: Optional[List[str]] = None,
    prompt_command: Optional[str] = None,
) -> Dict[str, Any]:
    event_flags = event_flags or {}
    now = datetime.now(timezone.utc).astimezone()
    timestamp_utc = now.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    date = now.strftime('%Y-%m-%d')
    skills = skills or []
    skills_text = ", ".join(skills) if skills else "-"
    subagents_text = "Orchestrator"
    invocation_reason = summary.strip() if summary.strip() else (prompt_command or "hook-triggered logging")
    prompt_normalization = "performed" if any(skill.lower() == 'prompt-optimizer' for skill in skills) else "not applicable"
    failure_detected = bool(event_flags.get('failure_detected'))
    outcome = "revise" if failure_detected else "pass"
    compaction_batch = f"CB-{now.strftime('%Y%m%d')}-01"

    defaults: Dict[str, Any] = {
        'timestamp_utc': timestamp_utc,
        'date': date,
        'request_type': 'chat-conversion',
        'routing_path': dispatch_path,
        'subagents': subagents_text,
        'subagent': subagents_text,
        'skills_used_ordered': skills_text,
        'skills_used': skills_text,
        'invocation_reason': invocation_reason,
        'outcome_impact': 'positive' if skills else 'neutral',
        'reuse_note': 'Use structured metadata payload for hook-driven logs.',
        'prompt_normalization': prompt_normalization,
        'model_selection': 'selected_model=unknown | task_type=orchestration-cycle | criticality=P2',
        'routing_mode': 'persistent=adaptive-score-based | effective=adaptive-score-based | source=default',
        'fallback_override': f"fallback_used={'yes' if event_flags.get('fallback_used') else 'no'} | fallback_reason={event_flags.get('fallback_reason', 'none')} | override_phrase={event_flags.get('override_phrase', 'none')}",
        'contract_score': 'n/a',
        'outcome': outcome,
        'failure_mode': 'hook reported failure' if failure_detected else 'none',
        'failure_mode_if_any': 'hook reported failure' if failure_detected else 'none',
        'root_cause_hypothesis': 'template field mapping was incomplete',
        'follow_up_action': 'Verify all template fields are populated from structured metadata.',
        'signal': summary or prompt_command or 'hook-triggered template render',
        'frequency': '1',
        'impact': 'logging fields populated',
        'affected_subagents': subagents_text,
        'likely_cause': 'missing structured metadata path',
        'proposed_policy_change': 'Render log templates from structured metadata payloads.',
        'priority': 'medium',
        'problem': 'blank template fields',
        'proposed_change': 'Populate log templates from hook metadata.',
        'scope': 'output-format',
        'safety_check': 'preview render and hook-runner invocation',
        'owner': 'Orchestrator',
        'project_request': summary or 'full-log template verification',
        'stage': 'checkpoint',
        'summary': summary or 'Hook-triggered logging cycle',
        'summary_completed': 'Structured fields are now available to the renderer.',
        'summary_in_progress': 'Verifying hook-driven log output.',
        'summary_blockers_risks': 'Upstream subagent capture still defaults to Orchestrator.',
        'summary_next_action': 'Run the hook preview and confirm field population.',
        'routing_policy_changes': 'mode_change=no | override=no | fallback=no',
        'change_applied': summary or 'Structured full-log template rendering',
        'expected_effect': 'Log templates receive populated field values.',
        'validation_window': 'preview render and hook invocation',
        'observed_result': 'Preview render should show populated fields.',
        'decision': 'keep' if not failure_detected else 'revise',
        'request_type_skill': 'chat-conversion',
        'compaction_batch': compaction_batch,
    }

    return {
        'defaults': defaults,
        'targets': {
            'Behavior-Log.md': {
                'request_type': 'chat-conversion',
                'subagent': subagents_text,
                'model_selection': defaults['model_selection'],
                'routing_mode': defaults['routing_mode'],
                'fallback_override': defaults['fallback_override'],
                'skills_used': skills_text,
                'prompt_normalization': prompt_normalization,
                'contract_score': defaults['contract_score'],
                'outcome': outcome,
                'failure_mode': defaults['failure_mode'],
                'failure_mode_if_any': defaults['failure_mode_if_any'],
                'root_cause_hypothesis': defaults['root_cause_hypothesis'],
                'follow_up_action': defaults['follow_up_action'],
                'compaction_batch': compaction_batch,
            },
            'Behavior-Patterns.md': {
                'signal': defaults['signal'],
                'frequency': defaults['frequency'],
                'impact': defaults['impact'],
                'affected_subagents': defaults['affected_subagents'],
                'likely_cause': defaults['likely_cause'],
                'proposed_policy_change': defaults['proposed_policy_change'],
                'status': 'candidate',
                'compaction_batch': compaction_batch,
            },
            'Learning-Backlog.md': {
                'priority': defaults['priority'],
                'problem': defaults['problem'],
                'proposed_change': defaults['proposed_change'],
                'scope': defaults['scope'],
                'safety_check': defaults['safety_check'],
                'owner': defaults['owner'],
                'status': 'in_progress',
            },
            'Project-Context-Log.md': {
                'project_request': defaults['project_request'],
                'stage': defaults['stage'],
                'summary': defaults['summary'],
                'completed': defaults['summary_completed'],
                'in_progress': defaults['summary_in_progress'],
                'blockers_risks': defaults['summary_blockers_risks'],
                'next_action': defaults['summary_next_action'],
                'routing_policy_changes': defaults['routing_policy_changes'],
            },
            'Runbook.md': {
                'date': date,
                'trigger_pattern': prompt_command or 'hook-triggered logging',
                'change_applied': defaults['change_applied'],
                'expected_effect': defaults['expected_effect'],
                'validation_window': defaults['validation_window'],
                'observed_result': defaults['observed_result'],
                'decision': defaults['decision'],
            },
            'Skill-Usage-Log.md': {
                'request_type': 'chat-conversion',
                'routing_path': dispatch_path,
                'subagents': subagents_text,
                'skills_used_ordered': skills_text,
                'invocation_reason': invocation_reason,
                'outcome_impact': defaults['outcome_impact'],
                'reuse_note': defaults['reuse_note'],
            },
        },
    }


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

    context = _build_log_context(
        dispatch_path=dispatch_path,
        event_flags=event_flags,
        summary=summary,
        skills=skills,
        prompt_command=prompt_command,
    )

    # If a specific prompt command was requested, run it directly.
    if prompt_command:
        proc = _run_log_command(
            repo_root,
            prompt_command,
            body,
            author=author,
            tags=tags,
            preview=preview,
            script_root=target_root,
            context=context,
        )
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
        proc = _run_log_command(
            repo_root,
            '/info',
            body,
            author=author,
            tags=tags,
            preview=preview,
            script_root=target_root,
            context=context,
        )
        return {"level": "compact", "command": "/info", "returncode": str(proc.returncode)}

    if level == 'full':
        proc = _run_log_command(
            repo_root,
            '/full-log',
            body,
            author=author,
            tags=tags,
            preview=preview,
            script_root=target_root,
            context=context,
        )
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

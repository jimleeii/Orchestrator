#!/usr/bin/env python3
"""Analyze orchestrator wiki logs and produce a structured metrics summary.

Reads Behavior-Log.md and Skill-Usage-Log.md from .wiki/orchestrator/ and outputs
a JSON object with key quality indicators over the trailing N cycles.

Usage
-----
    python scripts/analyze_logs.py
    python scripts/analyze_logs.py --wiki .wiki/orchestrator --cycles 30
    python scripts/analyze_logs.py --output metrics.json

Metrics returned
----------------
- avg_contract_score      Average contract score across scored cycles (None when no data)
- score_distribution      Counts bucketed into fail(<70), low(70-79), ok(80-89), good(90+)
- model_escalation_count  Cycles where tier_override fired due to low contract score
- cycle_success_rate      Fraction of cycles with non-failure status
- skill_usage_counts      Dict mapping skill name -> invocation count
- cycle_count             Total cycles analyzed
- stale_backlog_count     Learning-Backlog items older than --stale-days with no update
- window_cycles           N from --cycles flag
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Regex patterns for log entry fields
# ---------------------------------------------------------------------------

# Behavior-Log entry markers (cycle_id or OBS-style IDs)
_RE_CYCLE_ID = re.compile(r"\bCYC-\d{8}-\d{6}-[0-9A-F]{4}\b")
_RE_OBS_ID   = re.compile(r"###\s+(OBS|PAT|LRN|CTX|CHG)-\d{8}-\w+")
_RE_CONTRACT  = re.compile(r"contract_score[=:\s]+(\d+)", re.IGNORECASE)
_RE_TIER_OVR  = re.compile(r"tier_override[=:\s]+true", re.IGNORECASE)
_RE_STATUS    = re.compile(r"\bstatus[=:\s]+(success|partial|failure)\b", re.IGNORECASE)

# Skill-Usage-Log entry markers
_RE_SKL_ID    = re.compile(r"###\s+SKL-\d{8,14}")
_RE_SKL_SKILLS = re.compile(r"Skills Used \(ordered\):\s*(.+)", re.IGNORECASE)

# Learning-Backlog entry markers with date
_RE_BACKLOG_DATE = re.compile(r"(?:Date|Timestamp)[^\d]*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _find_default_wiki(start: Path | None = None) -> Path:
    """Locate repo-root .wiki/orchestrator by walking upward to .git."""
    cur = (start or Path(__file__)).resolve()
    cur = cur if cur.is_dir() else cur.parent
    for _ in range(20):
        if (cur / ".git").exists():
            return cur / ".wiki" / "orchestrator"
        if cur.parent == cur:
            break
        cur = cur.parent
    return Path(".wiki/orchestrator")


def _split_entries(text: str, entry_re: re.Pattern) -> list[str]:
    """Split a markdown log file into individual entry blocks."""
    positions = [m.start() for m in entry_re.finditer(text)]
    if not positions:
        return []
    blocks = []
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        blocks.append(text[start:end])
    return blocks


# ---------------------------------------------------------------------------
# Analyzers
# ---------------------------------------------------------------------------

def analyze_behavior_log(text: str, window: int) -> dict[str, Any]:
    """Extract contract scores, tier overrides, and status from Behavior-Log."""
    # Collect per-entry data
    scores: list[int] = []
    tier_overrides = 0
    status_counts: Counter[str] = Counter()

    # Split on either CYC- IDs or OBS-style headings
    combined_re = re.compile(r"(?:###\s+(?:OBS|PAT|LRN|CTX|CHG)-\d{8}|CYC-\d{8}-\d{6}-[0-9A-F]{4})")
    entries = _split_entries(text, combined_re)

    # Limit to trailing `window` entries
    entries = entries[-window:]

    for entry in entries:
        m = _RE_CONTRACT.search(entry)
        if m:
            scores.append(int(m.group(1)))

        if _RE_TIER_OVR.search(entry):
            tier_overrides += 1

        m2 = _RE_STATUS.search(entry)
        if m2:
            status_counts[m2.group(1).lower()] += 1

    total = len(entries)
    success = status_counts.get("success", 0)
    failure = status_counts.get("failure", 0)
    # cycles without explicit status are not counted against success rate
    rated = success + status_counts.get("partial", 0) + failure
    success_rate = round(success / rated, 3) if rated else None

    avg_score = round(sum(scores) / len(scores), 1) if scores else None
    distribution: dict[str, int] = {"fail": 0, "low": 0, "ok": 0, "good": 0}
    for s in scores:
        if s < 70:
            distribution["fail"] += 1
        elif s < 80:
            distribution["low"] += 1
        elif s < 90:
            distribution["ok"] += 1
        else:
            distribution["good"] += 1

    return {
        "cycle_count": total,
        "avg_contract_score": avg_score,
        "score_distribution": distribution,
        "scores_sampled": len(scores),
        "model_escalation_count": tier_overrides,
        "cycle_success_rate": success_rate,
        "status_counts": dict(status_counts),
    }


def analyze_skill_usage_log(text: str, window: int) -> dict[str, int]:
    """Count skill invocations from Skill-Usage-Log."""
    entries = _split_entries(text, _RE_SKL_ID)
    entries = entries[-window:]
    counts: Counter[str] = Counter()
    for entry in entries:
        m = _RE_SKL_SKILLS.search(entry)
        if not m:
            continue
        raw = m.group(1).strip()
        if raw in ("-", "none", ""):
            continue
        for skill in raw.split(","):
            name = skill.strip()
            if name:
                counts[name] += 1
    return dict(counts.most_common())


def count_stale_backlog(text: str, stale_days: int) -> int:
    """Count Learning-Backlog items whose last date is older than stale_days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
    stale = 0
    for m in _RE_BACKLOG_DATE.finditer(text):
        try:
            dt = datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
            if dt < cutoff:
                stale += 1
        except ValueError:
            pass
    return stale


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze orchestrator wiki logs and output metrics JSON")
    parser.add_argument("--wiki", default=str(_find_default_wiki()),
                        help="Path to .wiki/orchestrator directory (default: .wiki/orchestrator)")
    parser.add_argument("--cycles", type=int, default=30,
                        help="Number of trailing cycles to analyze (default: 30)")
    parser.add_argument("--stale-days", type=int, default=30,
                        help="Learning-Backlog items older than this many days are flagged (default: 30)")
    parser.add_argument("--output", help="Write JSON to this file instead of stdout")
    args = parser.parse_args(argv)

    wiki = Path(args.wiki)
    if not wiki.is_dir():
        print(f"error: wiki directory not found: {wiki}", file=sys.stderr)
        return 1

    behavior_text   = _read(wiki / "Behavior-Log.md")
    skill_text      = _read(wiki / "Skill-Usage-Log.md")
    backlog_text    = _read(wiki / "Learning-Backlog.md")

    behavior_stats  = analyze_behavior_log(behavior_text, args.cycles)
    skill_counts    = analyze_skill_usage_log(skill_text, args.cycles)
    stale_backlog   = count_stale_backlog(backlog_text, args.stale_days)

    metrics: dict[str, Any] = {
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "window_cycles": args.cycles,
        "stale_days": args.stale_days,
        **behavior_stats,
        "skill_usage_counts": skill_counts,
        "stale_backlog_count": stale_backlog,
    }

    output = json.dumps(metrics, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(f"Metrics written to {args.output}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

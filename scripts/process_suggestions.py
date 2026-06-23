#!/usr/bin/env python3
"""Process suggestion JSONL files into an evaluated Markdown report.

Usage:
  python scripts/process_suggestions.py --input suggestions.jsonl --output suggestions_evaluated/task.md

The script expects each line in the input to be a JSON object with at least:
  - text: the suggestion text
  - timestamp, task_id, author, step_id (optional)

It produces a Markdown file with a linkable TOC, numbered sections, and a
checklist of execution tasks that link back to suggestion sections.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from typing import List, Dict, Any


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                # skip malformed
                continue
            items.append(obj)
    return items


def slugify(text: str) -> str:
    # simple slug for anchors
    s = text.lower()
    s = s.replace(" ", "-")
    s = "".join(ch for ch in s if ch.isalnum() or ch == "-")
    return s[:64]


def render_markdown(task_id: str, suggestions: List[Dict[str, Any]]) -> str:
    now = datetime.utcnow().isoformat() + "Z"
    header = [f"# Suggestions Evaluated — task {task_id}", "", f"_Generated: {now}_", ""]

    # Table of contents
    toc = ["## Table of contents", "", "- [Execution checklist](#execution-checklist)", ""]
    for i, s in enumerate(suggestions, start=1):
        title = s.get("title") or (s.get("text") or "Suggestion").strip().splitlines()[0]
        anchor = f"suggestion-{i}-{slugify(title)}"
        toc.append(f"- [{i}. {title}](#{anchor})")
    toc.append("")

    # Execution checklist (checkboxes link to sections)
    checklist = ["## Execution checklist", ""]
    for i, s in enumerate(suggestions, start=1):
        title = s.get("title") or (s.get("text") or "Suggestion").strip().splitlines()[0]
        anchor = f"suggestion-{i}-{slugify(title)}"
        checklist.append(f"- [ ] [#{i} {title}](#{anchor})")
    checklist.append("")

    # Detailed numbered suggestions
    details = ["## Suggestions", ""]
    for i, s in enumerate(suggestions, start=1):
        title = s.get("title") or (s.get("text") or "Suggestion").strip().splitlines()[0]
        anchor = f"suggestion-{i}-{slugify(title)}"
        score = s.get("quality_score")
        meta_parts = []
        if s.get("author"):
            meta_parts.append(f"author={s.get('author')}")
        if s.get("step_id"):
            meta_parts.append(f"step={s.get('step_id')}")
        if score is not None:
            meta_parts.append(f"score={score}")
        meta = " | ".join(meta_parts)

        details.append(f"### {i}. {title}")
        details.append(f"<a id=\"{anchor}\"></a>")
        if meta:
            details.append(f"_{meta}_")
            details.append("")
        text = s.get("text") or ""
        details.append(text)
        details.append("")

    parts = header + toc + checklist + details
    return "\n".join(parts)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="Path to suggestions JSONL input file")
    parser.add_argument("--output", "-o", required=True, help="Path to output Markdown file")
    args = parser.parse_args(argv)

    items = load_jsonl(args.input)
    if not items:
        print("No suggestions found in input.")
        return 2

    # derive a task id from first item or fallback
    task_id = items[0].get("task_id") or items[0].get("cycle_id") or "unknown"
    md = render_markdown(task_id, items)

    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)

    # also write machine-readable sidecar
    sidecar = args.output + ".json"
    with open(sidecar, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Wrote {args.output} and {sidecar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

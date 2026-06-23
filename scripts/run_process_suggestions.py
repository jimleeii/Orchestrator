#!/usr/bin/env python3
"""Small helper to run the suggestion processor on the workspace suggestions.jsonl."""
import os
import sys
import subprocess

if __name__ == "__main__":
    repo = os.getcwd()
    proc_in = os.path.join(repo, ".suggestions", "suggestions.jsonl")
    if not os.path.exists(proc_in):
        print(f"No suggestions.jsonl at {proc_in}")
        sys.exit(2)
    out_dir = os.path.join(repo, "suggestions_evaluated")
    os.makedirs(out_dir, exist_ok=True)
    out_md = os.path.join(out_dir, "manual.md")
    runner = [sys.executable, os.path.join("scripts", "process_suggestions.py"), "-i", proc_in, "-o", out_md]
    res = subprocess.run(runner)
    sys.exit(res.returncode)

"""Ensure the repository root is on sys.path early during Python startup.

This file is intentionally placed at the repo root so the site module will
import it early and we can prioritize workspace-local imports during test
execution (avoids accidentally importing installed packages with the same
top-level names).
"""
import sys
import os

try:
    repo_root = os.path.abspath(os.path.dirname(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
except Exception:
    pass

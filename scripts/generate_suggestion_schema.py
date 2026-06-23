#!/usr/bin/env python3
"""Generate and persist suggestion JSON Schema from the pydantic model.

Writes to .suggestions/suggestion_schema.json by default.
"""
import argparse
import os
from pathlib import Path
import sys

# Ensure repo root is on sys.path so imports resolve to local modules before any installed packages
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=".suggestions/suggestion_schema.json")
    args = parser.parse_args(argv)

    try:
        from src.orchestrator_runtime import export_suggestion_json_schema
    except Exception:
        try:
            from orchestrator_runtime import export_suggestion_json_schema  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"Could not import orchestrator_runtime.export_suggestion_json_schema: {exc}")

    out = os.path.abspath(args.output)
    export_suggestion_json_schema(out)
    print(f"Wrote suggestion JSON Schema to: {out}")


if __name__ == "__main__":
    main()

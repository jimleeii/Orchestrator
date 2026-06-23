#!/usr/bin/env python3
"""Compare generated suggestion schema with committed file (normalized JSON)."""
import json
import sys
import os
import difflib


def main():
    committed = ".suggestions/suggestion_schema.json"
    generated = ".suggestions/suggestion_schema.generated.json"
    print(f"Comparing generated schema with committed {committed} (normalized JSON, sort keys)")
    if not os.path.exists(committed):
        print(f"ERROR: Committed {committed} is missing", file=sys.stderr)
        return 2
    if not os.path.exists(generated):
        print(f"ERROR: Generated {generated} is missing", file=sys.stderr)
        return 3
    with open(committed, "r", encoding="utf-8") as f:
        a = json.load(f)
    with open(generated, "r", encoding="utf-8") as f:
        b = json.load(f)
    na = json.dumps(a, sort_keys=True, separators=(",", ":"))
    nb = json.dumps(b, sort_keys=True, separators=(",", ":"))
    if na != nb:
        aa = json.dumps(a, sort_keys=True, indent=2)
        bb = json.dumps(b, sort_keys=True, indent=2)
        print(
            "The suggestion schema committed in the repo is out of date. Regenerate using: python scripts/generate_suggestion_schema.py --output .suggestions/suggestion_schema.json",
            file=sys.stderr,
        )
        for line in difflib.unified_diff(
            aa.splitlines(), bb.splitlines(), fromfile=committed + " (normalized)", tofile=generated + " (normalized)", lineterm="",
        ):
            print(line)
        return 1
    print("Schemas match (normalized)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

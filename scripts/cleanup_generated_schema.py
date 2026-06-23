#!/usr/bin/env python3
"""Cleanup generated suggestion schema file if present."""
import os


def main():
    path = ".suggestions/suggestion_schema.generated.json"
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
    print("cleanup done")


if __name__ == "__main__":
    raise SystemExit(main())

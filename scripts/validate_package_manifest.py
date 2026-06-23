#!/usr/bin/env python3
"""Validate that Orchestrator.zip contains a non-empty skills_manifest.json."""
import sys
import zipfile
import json


def main():
    zpath = "Orchestrator.zip"
    try:
        z = zipfile.ZipFile(zpath)
    except Exception as e:
        print("Failed to open", zpath, e)
        return 1
    candidates = [n for n in z.namelist() if n.endswith("skills_manifest.json")]
    if not candidates:
        print("ERROR: skills_manifest.json not found in package")
        return 2
    data = z.read(candidates[0]).decode("utf-8")
    try:
        j = json.loads(data)
    except Exception as e:
        print("ERROR: skills_manifest.json is not valid JSON:", e)
        return 3
    if not isinstance(j, dict) or len(j) == 0:
        print("ERROR: skills_manifest.json is empty or contains no skills")
        return 4
    print(
        "OK: skills_manifest.json found and contains",
        len(j),
        "skills (sample keys:", list(j.keys())[:10], ")",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

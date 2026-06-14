#!/usr/bin/env python3
"""API contract validator: verify documentation matches runtime.

Validates that DISPATCH_AND_LOGGING_API.md examples and status enums
match the actual runtime implementation in src/orchestrator_runtime.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Set


def _extract_status_values_from_runtime(runtime_file: Path) -> Set[str]:
    """Extract all status values assigned in orchestrator_runtime."""
    try:
        content = runtime_file.read_text(encoding='utf-8')
    except Exception as e:
        print(f"ERROR: Failed to read {runtime_file}: {e}")
        return set()
    
    # Match patterns like: "status": "value"
    pattern = r'"status":\s*"([^"]+)"'
    matches = re.findall(pattern, content)
    return set(matches)


def _extract_status_values_from_docs(docs_file: Path) -> Set[str]:
    """Extract all status values mentioned in documentation."""
    try:
        content = docs_file.read_text(encoding='utf-8')
    except Exception as e:
        print(f"ERROR: Failed to read {docs_file}: {e}")
        return set()
    
    # Look for patterns like: "status": "value" or status == "value" or | `value` |
    patterns = [
        r'"status":\s*"([^"]+)"',          # "status": "value"
        r'status.*==\s*"([^"]+)"',         # status == "value"
        r'\|\s*`([^`]+)`\s*\|',            # | `value` | (table)
        r'\|\s*"([^"]+)"\s*\|',            # | "value" | (table)
    ]
    
    status_values = set()
    for pattern in patterns:
        matches = re.findall(pattern, content)
        status_values.update(matches)
    
    # Filter to only known status values (exclude action values, booleans, etc.)
    known_statuses = {
        'direct-complete', 'success', 'failure', 'not-run', 'retry-budget-exhausted'
    }
    return status_values & known_statuses


def validate_api_contract(workspace_root: Path) -> int:
    """Validate that API docs match runtime implementation.
    
    Returns 0 if contract is valid, 1 if mismatches found.
    """
    api_docs = workspace_root / "DISPATCH_AND_LOGGING_API.md"
    runtime_file = workspace_root / "src" / "orchestrator_runtime.py"
    
    if not api_docs.exists():
        print(f"ERROR: API docs not found: {api_docs}")
        return 1
    
    if not runtime_file.exists():
        print(f"ERROR: Runtime file not found: {runtime_file}")
        return 1
    
    print("Validating API contract...")
    print(f"  Docs:    {api_docs.name}")
    print(f"  Runtime: {runtime_file.relative_to(workspace_root)}")
    
    runtime_statuses = _extract_status_values_from_runtime(runtime_file)
    docs_statuses = _extract_status_values_from_docs(api_docs)
    
    print(f"\n📋 Status values found:")
    print(f"  Runtime:  {sorted(runtime_statuses)}")
    print(f"  Docs:     {sorted(docs_statuses)}")
    
    runtime_only = runtime_statuses - docs_statuses
    docs_only = docs_statuses - runtime_statuses
    both = runtime_statuses & docs_statuses
    
    print(f"\n✓ Common:  {len(both)} status values documented correctly")
    
    has_drift = bool(runtime_only or docs_only)
    
    if runtime_only:
        print(f"\n⚠ RUNTIME-ONLY: Status values in code but not docs:")
        for status in sorted(runtime_only):
            print(f"    • \"{status}\"")
    
    if docs_only:
        print(f"\n⚠ DOCS-ONLY: Status values in docs but not code:")
        for status in sorted(docs_only):
            print(f"    • \"{status}\"")
    
    if has_drift:
        print(f"\n❌ Contract validation FAILED")
        print("   Fix: Update DISPATCH_AND_LOGGING_API.md to match runtime status values")
        return 1
    else:
        print(f"\n✓ Contract validation PASSED")
        return 0


if __name__ == "__main__":
    workspace_root = Path(__file__).resolve().parents[1]
    exit_code = validate_api_contract(workspace_root)
    sys.exit(exit_code)

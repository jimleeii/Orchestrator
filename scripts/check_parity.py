#!/usr/bin/env python3
"""Orchestrator root↔mirror parity checker.

This script verifies that critical files remain synchronized between the root
Orchestrator package location and its potential mirror at `.github/agents/Orchestrator/`.

Critical parity surface (source-of-truth locations):
  - src/          (runtime source code)
  - hooks/        (hook implementations)
  - scripts/      (helper scripts)
  - rules/        (policy files)
  - *.md          (documentation)
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def _hash_file(fpath: Path, algorithm: str = 'sha256') -> str:
    """Compute hash of file contents."""
    hasher = hashlib.new(algorithm)
    try:
        with open(fpath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        return f"ERROR: {e}"


def _collect_parity_surface_hashes(root: Path) -> Dict[str, str]:
    """Collect file hashes for the critical parity surface."""
    hashes = {}

    # Define critical folders and patterns
    critical_patterns = [
        ('src', '**/*.py'),
        ('hooks', '**/*.py'),
        ('scripts', '*.py'),
        ('rules', '*.md'),
    ]

    for folder, pattern in critical_patterns:
        folder_path = root / folder
        if folder_path.exists():
            for filepath in sorted(folder_path.glob(pattern)):
                if filepath.is_file():
                    rel_path = filepath.relative_to(root)
                    file_hash = _hash_file(filepath)
                    hashes[str(rel_path)] = file_hash

    # Also include root-level documentation
    for readme_name in ['AGENTS.md', 'CLAUDE.md', 'DISPATCH_AND_LOGGING_API.md']:
        readme_path = root / readme_name
        if readme_path.exists():
            file_hash = _hash_file(readme_path)
            hashes[readme_name] = file_hash

    return hashes


def _compare_parity(root_hashes: Dict[str, str], mirror_hashes: Dict[str, str]) -> Tuple[List[str], List[str], List[str]]:
    """Compare parity between root and mirror.

    Returns (mismatches, root_only, mirror_only)
    """
    mismatches = []
    root_only = []
    mirror_only = []

    all_keys = set(root_hashes.keys()) | set(mirror_hashes.keys())

    for key in sorted(all_keys):
        root_hash = root_hashes.get(key)
        mirror_hash = mirror_hashes.get(key)

        if root_hash is None:
            mirror_only.append(key)
        elif mirror_hash is None:
            root_only.append(key)
        elif root_hash != mirror_hash:
            mismatches.append(key)

    return mismatches, root_only, mirror_only


def check_orchestrator_parity(workspace_root: Path) -> int:
    """Check parity between root and mirror Orchestrator packages.

    Returns 0 if parity is maintained, 1 if drift detected.
    """
    root_orch = workspace_root
    mirror_orch = workspace_root / ".github" / "agents" / "Orchestrator"

    if not mirror_orch.exists():
        print("ℹ  Mirror Orchestrator not found at .github/agents/Orchestrator (optional)")
        return 0

    print(f"Checking Orchestrator parity...")
    print(f"  Root:   {root_orch}")
    print(f"  Mirror: {mirror_orch}")

    root_hashes = _collect_parity_surface_hashes(root_orch)
    mirror_hashes = _collect_parity_surface_hashes(mirror_orch)

    mismatches, root_only, mirror_only = _compare_parity(root_hashes, mirror_hashes)

    has_drift = bool(mismatches or root_only or mirror_only)

    if mismatches:
        print(f"\n❌ PARITY VIOLATION: {len(mismatches)} file(s) have different content:")
        for fname in mismatches[:10]:  # Show first 10
            print(f"    ✗ {fname}")
        if len(mismatches) > 10:
            print(f"    ... and {len(mismatches) - 10} more")

    if root_only:
        print(f"\n⚠ ROOT-ONLY: {len(root_only)} file(s) exist in root but not mirror:")
        for fname in root_only[:5]:
            print(f"    • {fname}")
        if len(root_only) > 5:
            print(f"    ... and {len(root_only) - 5} more")

    if mirror_only:
        print(f"\n⚠ MIRROR-ONLY: {len(mirror_only)} file(s) exist in mirror but not root:")
        for fname in mirror_only[:5]:
            print(f"    • {fname}")
        if len(mirror_only) > 5:
            print(f"    ... and {len(mirror_only) - 5} more")

    if has_drift:
        print(f"\n❌ Parity check FAILED")
        return 1
    else:
        print(f"\n✓ Parity check PASSED")
        return 0


def main(argv: List[str] | None = None) -> int:
    _ = argv
    workspace_root = Path(__file__).resolve().parents[1]
    return check_orchestrator_parity(workspace_root)


if __name__ == "__main__":
    sys.exit(main())

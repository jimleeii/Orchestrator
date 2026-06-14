"""Tests for the parity checker.

Verifies that the parity checker correctly identifies mismatches,
root-only files, and mirror-only files.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ParityCheckerTests(unittest.TestCase):
    """Test the parity checking logic."""

    def test_parity_check_returns_zero_when_mirror_missing(self) -> None:
        """Test case: when mirror doesn't exist, check should pass (return 0)."""
        # Import here to avoid issues if module doesn't exist yet
        try:
            from scripts import check_parity
        except ImportError:
            self.skipTest("check_parity module not available")
        
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            temp_root = Path(temp_dir)
            
            # Create root structure without mirror
            (temp_root / "src").mkdir()
            (temp_root / "hooks").mkdir()
            (temp_root / "scripts").mkdir()
            (temp_root / "rules").mkdir()
            
            # Create some files
            (temp_root / "src" / "test.py").write_text("# test")
            (temp_root / "AGENTS.md").write_text("# Agents")
            
            result = check_parity.check_orchestrator_parity(temp_root)
            self.assertEqual(result, 0, "Parity check should pass when mirror missing")

    def test_parity_check_detects_missing_mirror_files(self) -> None:
        """Test case: files exist in root but not mirror."""
        try:
            from scripts import check_parity
        except ImportError:
            self.skipTest("check_parity module not available")
        
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            temp_root = Path(temp_dir)
            
            # Create root structure
            (temp_root / "src").mkdir()
            (temp_root / "src" / "test.py").write_text("# test")
            (temp_root / "hooks").mkdir()
            (temp_root / "scripts").mkdir()
            (temp_root / "rules").mkdir()
            
            # Create mirror with subset of files
            mirror = temp_root / ".github" / "agents" / "Orchestrator"
            (mirror / "src").mkdir(parents=True)
            (mirror / "hooks").mkdir(parents=True)
            (mirror / "scripts").mkdir(parents=True)
            (mirror / "rules").mkdir(parents=True)
            # Note: src/test.py is NOT created in mirror
            
            result = check_parity.check_orchestrator_parity(temp_root)
            self.assertEqual(result, 1, "Parity check should fail when files missing from mirror")

    def test_parity_check_detects_content_mismatch(self) -> None:
        """Test case: same file has different content in root vs mirror."""
        try:
            from scripts import check_parity
        except ImportError:
            self.skipTest("check_parity module not available")
        
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            temp_root = Path(temp_dir)
            
            # Create root structure
            (temp_root / "src").mkdir()
            (temp_root / "src" / "test.py").write_text("# root version")
            (temp_root / "hooks").mkdir()
            (temp_root / "scripts").mkdir()
            (temp_root / "rules").mkdir()
            (temp_root / "AGENTS.md").write_text("# Root")
            
            # Create mirror with same structure but different content
            mirror = temp_root / ".github" / "agents" / "Orchestrator"
            (mirror / "src").mkdir(parents=True)
            (mirror / "src" / "test.py").write_text("# mirror version")  # Different!
            (mirror / "hooks").mkdir(parents=True)
            (mirror / "scripts").mkdir(parents=True)
            (mirror / "rules").mkdir(parents=True)
            (mirror / "AGENTS.md").write_text("# Mirror")  # Different!
            
            result = check_parity.check_orchestrator_parity(temp_root)
            self.assertEqual(result, 1, "Parity check should fail on content mismatch")

    def test_parity_check_passes_when_identical(self) -> None:
        """Test case: root and mirror have identical content."""
        try:
            from scripts import check_parity
        except ImportError:
            self.skipTest("check_parity module not available")
        
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            temp_root = Path(temp_dir)
            
            # Create root structure
            (temp_root / "src").mkdir()
            (temp_root / "src" / "test.py").write_text("# shared")
            (temp_root / "hooks").mkdir()
            (temp_root / "scripts").mkdir()
            (temp_root / "rules").mkdir()
            (temp_root / "AGENTS.md").write_text("# Shared")
            
            # Create mirror with IDENTICAL content
            mirror = temp_root / ".github" / "agents" / "Orchestrator"
            (mirror / "src").mkdir(parents=True)
            (mirror / "src" / "test.py").write_text("# shared")  # Identical
            (mirror / "hooks").mkdir(parents=True)
            (mirror / "scripts").mkdir(parents=True)
            (mirror / "rules").mkdir(parents=True)
            (mirror / "AGENTS.md").write_text("# Shared")  # Identical
            
            result = check_parity.check_orchestrator_parity(temp_root)
            self.assertEqual(result, 0, "Parity check should pass when content is identical")

    def test_collect_parity_surface_hashes_finds_python_files(self) -> None:
        """Test case: hash collector finds Python files in critical folders."""
        try:
            from scripts import check_parity
        except ImportError:
            self.skipTest("check_parity module not available")
        
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            temp_root = Path(temp_dir)
            
            # Create structure with Python files
            (temp_root / "src").mkdir()
            (temp_root / "src" / "module.py").write_text("# src module")
            (temp_root / "hooks").mkdir()
            (temp_root / "hooks" / "hook.py").write_text("# hook")
            (temp_root / "scripts").mkdir()
            (temp_root / "scripts" / "helper.py").write_text("# helper")
            (temp_root / "rules").mkdir()
            (temp_root / "rules" / "policy.md").write_text("# policy")
            
            hashes = check_parity._collect_parity_surface_hashes(temp_root)
            
            # Should find all critical files (use str.replace to normalize path separators)
            found_keys = {str(k).replace(chr(92), '/') for k in hashes.keys()}
            self.assertIn("src/module.py", found_keys)
            self.assertIn("hooks/hook.py", found_keys)
            self.assertIn("scripts/helper.py", found_keys)
            self.assertIn("rules/policy.md", found_keys)
            
            # Hashes should be valid hex strings
            for fpath, file_hash in hashes.items():
                self.assertRegex(file_hash, r'^[a-f0-9]{64}$', 
                               f"Invalid hash for {fpath}: {file_hash}")


if __name__ == "__main__":
    unittest.main()

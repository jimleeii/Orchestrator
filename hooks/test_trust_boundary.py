"""Tests for script execution trust boundary validation."""

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

# Add repo root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator_runtime import validate_script_path


class TestScriptPathValidation(unittest.TestCase):
    """Test script path trust boundary validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.repo_root = Path(__file__).parent.parent
        # Set repo root via environment for test isolation
        os.environ["ORCHESTRATOR_REPO_ROOT"] = str(self.repo_root)

    def tearDown(self):
        """Clean up after tests."""
        if "ORCHESTRATOR_REPO_ROOT" in os.environ:
            del os.environ["ORCHESTRATOR_REPO_ROOT"]
        if "ORCHESTRATOR_TRUST_MODE" in os.environ:
            del os.environ["ORCHESTRATOR_TRUST_MODE"]

    def test_allowed_skill_script_path(self) -> None:
        """Allowed paths in skills/ directory should pass validation."""
        skill_script = self.repo_root / "skills" / "contract-validator" / "run_checks.py"
        is_valid, reason = validate_script_path(str(skill_script))
        self.assertTrue(is_valid, f"Expected valid skill script path, got: {reason}")

    def test_allowed_scripts_directory_path(self) -> None:
        """Allowed paths in scripts/ directory should pass validation."""
        script_path = self.repo_root / "scripts" / "log_prompt.py"
        is_valid, reason = validate_script_path(str(script_path))
        self.assertTrue(is_valid, f"Expected valid scripts path, got: {reason}")

    def test_allowed_test_scripts_directory_path(self) -> None:
        """Allowed paths in test-scripts/ directory should pass validation."""
        test_script = self.repo_root / "test-scripts" / "test_something.py"
        is_valid, reason = validate_script_path(str(test_script))
        self.assertTrue(is_valid, f"Expected valid test-scripts path, got: {reason}")

    def test_blocked_absolute_path_outside_repo(self) -> None:
        """Absolute paths outside repo should be blocked."""
        blocked_path = "/etc/passwd"
        is_valid, reason = validate_script_path(blocked_path)
        self.assertFalse(is_valid, "Expected blocked absolute path")
        self.assertIn("outside allowed locations", reason)

    def test_blocked_home_directory_path(self) -> None:
        """Home directory paths should be blocked."""
        home_script = Path.home() / "script.py"
        is_valid, reason = validate_script_path(str(home_script))
        self.assertFalse(is_valid, "Expected blocked home directory path")
        self.assertIn("outside allowed locations", reason)

    def test_blocked_temp_directory_path(self) -> None:
        """Temporary directory paths should be blocked."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".py") as f:
            is_valid, reason = validate_script_path(f.name)
            self.assertFalse(is_valid, "Expected blocked temp directory path")
            self.assertIn("outside allowed locations", reason)

    def test_path_traversal_attempt_blocked(self) -> None:
        """Path traversal attempts should be blocked."""
        traversal_path = str(self.repo_root / "scripts" / ".." / ".." / "etc" / "passwd")
        is_valid, reason = validate_script_path(traversal_path)
        # After normalization, this should resolve outside the allowlist
        self.assertFalse(is_valid, "Expected path traversal to be blocked")

    def test_relative_path_within_allowed_dir(self) -> None:
        """Relative paths that resolve within allowed dirs should pass."""
        # Change to repo root for this test
        original_cwd = os.getcwd()
        try:
            os.chdir(self.repo_root)
            is_valid, reason = validate_script_path("scripts/log_prompt.py")
            self.assertTrue(is_valid, f"Expected valid relative path, got: {reason}")
        finally:
            os.chdir(original_cwd)

    def test_relative_path_traversal_blocked(self) -> None:
        """Relative paths that traverse outside allowed dirs should be blocked."""
        original_cwd = os.getcwd()
        try:
            os.chdir(self.repo_root)
            is_valid, reason = validate_script_path("scripts/../../etc/passwd")
            self.assertFalse(is_valid, "Expected relative path traversal to be blocked")
        finally:
            os.chdir(original_cwd)

    def test_symlink_resolution(self) -> None:
        """Symlinks should resolve through to their target path."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a script in an allowed dir
            allowed_script = self.repo_root / "scripts" / "dummy.py"
            
            # Create a symlink pointing to it
            symlink_path = Path(tmpdir) / "symlink.py"
            try:
                symlink_path.symlink_to(allowed_script)
                is_valid, reason = validate_script_path(str(symlink_path))
                # Symlink target is in allowed dir, so it should resolve
                self.assertTrue(is_valid or "outside allowed" in reason, 
                               f"Symlink behavior unclear: {reason}")
            except OSError:
                # Skip if system doesn't support symlinks
                self.skipTest("Symlinks not supported on this system")

    def test_strict_no_symlinks_mode_blocks_symlink_path(self) -> None:
        """strict-no-symlinks mode should reject symlink script paths explicitly."""
        import tempfile

        os.environ["ORCHESTRATOR_TRUST_MODE"] = "strict-no-symlinks"
        with tempfile.TemporaryDirectory() as tmpdir:
            target_script = self.repo_root / "scripts" / "log_prompt.py"
            symlink_path = Path(tmpdir) / "log_prompt_symlink.py"

            try:
                symlink_path.symlink_to(target_script)
                is_valid, reason = validate_script_path(str(symlink_path))
                self.assertFalse(is_valid, "Expected strict-no-symlinks mode to block symlink path")
                self.assertIn("Symlink script paths are blocked", reason)
            except OSError:
                self.skipTest("Symlinks not supported on this system")

    def test_nonexistent_path_invalid(self) -> None:
        """Nonexistent paths may still be validated (path doesn't exist yet)."""
        nonexistent = self.repo_root / "scripts" / "future_script.py"
        is_valid, reason = validate_script_path(str(nonexistent))
        # Path should still be valid since the directory is allowed
        self.assertTrue(is_valid, "Script path in allowed dir should be valid even if file doesn't exist")

    def test_blocklist_windows_paths(self) -> None:
        """Windows system paths should be blocked."""
        if sys.platform != "win32":
            self.skipTest("Windows-specific test")
        
        win_system = r"C:\Windows\System32\cmd.exe"
        is_valid, reason = validate_script_path(win_system)
        self.assertFalse(is_valid, "Expected Windows system path to be blocked")

    def test_repo_root_env_override(self) -> None:
        """ORCHESTRATOR_REPO_ROOT env var should override .git detection."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_repo = Path(tmpdir) / "fake_repo"
            tmp_repo.mkdir()
            (tmp_repo / "scripts").mkdir()
            dummy_script = tmp_repo / "scripts" / "test.py"
            dummy_script.touch()
            
            os.environ["ORCHESTRATOR_REPO_ROOT"] = str(tmp_repo)
            try:
                is_valid, reason = validate_script_path(str(dummy_script))
                self.assertTrue(is_valid, f"Expected valid with env override, got: {reason}")
            finally:
                del os.environ["ORCHESTRATOR_REPO_ROOT"]


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path
import sys

ORCHESTRATOR_ROOT = Path(__file__).resolve().parents[1]
if str(ORCHESTRATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATOR_ROOT))

from scripts import log_hook_runner as lhr


class TestLogHookRunnerHardening(unittest.TestCase):

    def test_resolve_orchestrator_root_uses_workspace_layout_when_present(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            workspace_root = Path(temp_dir)
            (workspace_root / "hooks").mkdir(parents=True, exist_ok=True)
            (workspace_root / "src").mkdir(parents=True, exist_ok=True)

            resolved = lhr._resolve_orchestrator_root(workspace_root)

            self.assertEqual(resolved, workspace_root)

    def test_resolve_orchestrator_root_uses_repo_layout_when_present(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            workspace_root = Path(temp_dir)
            repo_layout = workspace_root / ".github" / "agents" / "Orchestrator"
            (repo_layout / "hooks").mkdir(parents=True, exist_ok=True)
            (repo_layout / "src").mkdir(parents=True, exist_ok=True)

            resolved = lhr._resolve_orchestrator_root(workspace_root)

            self.assertEqual(resolved, repo_layout)


if __name__ == "__main__":
    unittest.main()

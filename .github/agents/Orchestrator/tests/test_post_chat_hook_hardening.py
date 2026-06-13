import sys
import tempfile
import unittest
from pathlib import Path

ORCHESTRATOR_ROOT = Path(__file__).resolve().parents[1]
if str(ORCHESTRATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATOR_ROOT))

from scripts import post_chat_hook as pch


class TestPostChatHookHardening(unittest.TestCase):

    def test_resolve_runner_uses_repo_layout_fallback(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            workspace_root = Path(temp_dir)
            orchestrator_root = workspace_root / "standalone-orchestrator"
            orchestrator_root.mkdir(parents=True, exist_ok=True)

            repo_runner = workspace_root / ".github" / "agents" / "Orchestrator" / "scripts" / "log_hook_runner.py"
            repo_runner.parent.mkdir(parents=True, exist_ok=True)
            repo_runner.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

            resolved = pch._resolve_runner(orchestrator_root, workspace_root)

            self.assertEqual(resolved, repo_runner)


if __name__ == "__main__":
    unittest.main()

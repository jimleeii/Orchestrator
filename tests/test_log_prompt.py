import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


class TestLogPromptTemplates(unittest.TestCase):

    def _run_preview(self, repo_root: Path, command: str, message: str) -> str:
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'log_prompt.py'
        completed = subprocess.run(
            [sys.executable, str(script), command, message, '--preview', '--root', str(repo_root)],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout

    def test_full_log_uses_per_target_templates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            prompts_dir = repo_root / '.github' / 'prompts'
            prompts_dir.mkdir(parents=True, exist_ok=True)
            (prompts_dir / 'full-log.prompt.md').write_text(
                textwrap.dedent(
                    '''
                    ---
                    description: "Append a full log entry across the orchestrator log set"
                    ---

                    Behavior-Log.md

                    ```yaml
                    entry_template: |
	### OBS-YYYYMMDD-XXX

	- Marker: behavior
                    ```

                    Runbook.md

                    ```yaml
                    entry_template: |
	### CHG-YYYYMMDD-XXX

	- Marker: runbook
                    ```
                    '''
                ).strip()
                + '\n',
                encoding='utf-8',
            )

            output = self._run_preview(repo_root, '/full-log', 'multi-template smoke test')

            self.assertIn('Behavior-Log.md', output)
            self.assertIn('Marker: behavior', output)
            self.assertIn('Runbook.md', output)
            self.assertIn('Marker: runbook', output)

    def test_single_template_fallback_still_works(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            prompts_dir = repo_root / '.github' / 'prompts'
            prompts_dir.mkdir(parents=True, exist_ok=True)
            (prompts_dir / 'runbook.prompt.md').write_text(
                textwrap.dedent(
                    '''
                    ---
                    description: "Append a runbook change record"
                    ---

                    ```yaml
                    entry_template: |
	### CHG-YYYYMMDD-XXX

	- Marker: default-runbook
	- Change Applied:
                    ```
                    '''
                ).strip()
                + '\n',
                encoding='utf-8',
            )

            output = self._run_preview(repo_root, '/runbook', 'fallback smoke test')

            self.assertIn('Marker: default-runbook', output)
            self.assertIn('Change Applied: fallback smoke test', output)

    def test_hook_runner_populates_context_fields(self):
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / 'scripts' / 'log_hook_runner.py'
        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                '--phase', 'post',
                '--summary', 'Hook field fill test',
                '--skills', 'prompt-optimizer,contract-validator',
                '--author', 'tester',
                '--force-persist',
                '--preview',
                '--root', str(repo_root),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        output = completed.stdout
        self.assertIn('Request Type: chat-conversion', output)
        self.assertIn('Subagent(s): Orchestrator', output)
        self.assertIn('Skills Used (ordered): prompt-optimizer, contract-validator', output)
        self.assertIn('Invocation Reason: Hook field fill test', output)
        self.assertIn('Outcome Impact: positive', output)


if __name__ == '__main__':
    unittest.main()
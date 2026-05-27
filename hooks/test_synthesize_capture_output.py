import json
import time
from pathlib import Path

import hooks.log_hooks as log_hooks


def _write_stdout_err_script(path: Path) -> None:
    path.write_text("""import sys
import time

print('hello stdout')
print('hello stderr', file=sys.stderr)
# small sleep to ensure writer flush
time.sleep(0.1)
""", encoding='utf-8')


def test_synthesize_captures_output(tmp_path: Path):
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    wiki_dir = repo_root / ".wiki" / "orchestrator"
    scripts_dir.mkdir(parents=True)
    wiki_dir.mkdir(parents=True)

    synth_script = scripts_dir / "synthesize_wiki.py"
    _write_stdout_err_script(synth_script)

    config = {"auto_synthesize_on_persist": True, "synthesis_logging": True, "synthesis_capture_output": True}
    (wiki_dir / "config.json").write_text(json.dumps(config), encoding='utf-8')

    # Run synth (non-preview); it should create a log file under .wiki/orchestrator/synthesis_logs/
    log_hooks._run_synthesize_wiki(repo_root, target_root=None, preview=False)

    logs_dir = wiki_dir / 'synthesis_logs'
    # Wait up to 2s for the log file to appear and be populated
    deadline = time.time() + 2.0
    files = []
    while time.time() < deadline:
        files = sorted(logs_dir.glob('synth-*.log')) if logs_dir.exists() else []
        if files:
            # check if file has content
            content = files[-1].read_bytes()
            if content:
                text = content.decode('utf-8', errors='ignore')
                assert 'hello stdout' in text
                assert 'hello stderr' in text
                return
        time.sleep(0.05)

    raise AssertionError('No synth log file with output was produced')

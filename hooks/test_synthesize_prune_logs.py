import json
import os
import time
from pathlib import Path

import hooks.log_hooks as log_hooks


def _write_minimal_script(path: Path) -> None:
    path.write_text("""import sys

if __name__ == '__main__':
    # minimal script that exits immediately
    sys.exit(0)
""", encoding='utf-8')


def test_synthesize_prunes_old_logs(tmp_path: Path):
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    wiki_dir = repo_root / ".wiki" / "orchestrator"
    scripts_dir.mkdir(parents=True)
    wiki_dir.mkdir(parents=True)

    synth_script = scripts_dir / "synthesize_wiki.py"
    _write_minimal_script(synth_script)

    logs_dir = wiki_dir / 'synthesis_logs'
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Create an old log file that should be pruned
    old_log = logs_dir / 'synth-old.log'
    old_log.write_text('old', encoding='utf-8')
    # set mtime to 2 days ago
    two_days = 2 * 24 * 60 * 60
    old_mtime = time.time() - two_days
    os.utime(old_log, times=(old_mtime, old_mtime))

    # Config: enable capture and set retention to 1 day
    config = {
        "auto_synthesize_on_persist": True,
        "synthesis_logging": True,
        "synthesis_capture_output": True,
        "synthesis_capture_retention_days": 1,
    }
    (wiki_dir / "config.json").write_text(json.dumps(config), encoding='utf-8')

    # Run synth (non-preview); prune should run and remove the old file
    log_hooks._run_synthesize_wiki(repo_root, target_root=None, preview=False)

    # Wait a short while for background work to complete
    deadline = time.time() + 2.0
    while time.time() < deadline:
        if not old_log.exists():
            break
        time.sleep(0.05)

    assert not old_log.exists(), 'Old synth log was not pruned'

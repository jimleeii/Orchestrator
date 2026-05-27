import json
from pathlib import Path

import hooks.log_hooks as log_hooks


def _write_minimal_script(path: Path) -> None:
    path.write_text("""import sys

if __name__ == '__main__':
    # minimal script that exits immediately
    sys.exit(0)
""", encoding='utf-8')


def test_synthesize_respects_config(tmp_path: Path):
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    wiki_dir = repo_root / ".wiki" / "orchestrator"
    scripts_dir.mkdir(parents=True)
    wiki_dir.mkdir(parents=True)

    synth_script = scripts_dir / "synthesize_wiki.py"
    _write_minimal_script(synth_script)

    # 1) disabled auto synth -> no log written
    config = {"auto_synthesize_on_persist": False, "synthesis_logging": True}
    (wiki_dir / "config.json").write_text(json.dumps(config), encoding='utf-8')
    log_hooks._run_synthesize_wiki(repo_root, target_root=None, preview=False)
    log_path = wiki_dir / ".synthesis_runs.log"
    assert not log_path.exists(), "Log should not be created when auto_synthesize_on_persist is false"

    # 2) enabled auto synth -> log created with START entry
    config["auto_synthesize_on_persist"] = True
    (wiki_dir / "config.json").write_text(json.dumps(config), encoding='utf-8')
    log_hooks._run_synthesize_wiki(repo_root, target_root=None, preview=False)
    assert log_path.exists(), "Log should be created when auto_synthesize_on_persist is true"
    content = log_path.read_text(encoding='utf-8')
    assert "START pid=" in content, f"Unexpected log content: {content!r}"

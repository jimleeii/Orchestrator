import os
import json
import sys
import shutil
from pathlib import Path
from src.orchestrator_runtime import persist_cycle


def test_follow_plan_suggestion_capture(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    # create hooks package with log_hooks.py
    hooks_dir = project / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "__init__.py").write_text("# hooks package")
    log_hooks_py = '''import os, json

def normalize_checkpoint_metadata(summary, metadata, event_flags):
    return metadata

def log_cycle(dispatch_path, event_flags, summary, skills, metadata, transcript, force_persist_all, author, target_root):
    os.makedirs(target_root, exist_ok=True)
    out = {"summary": summary, "transcript": transcript, "metadata": metadata}
    with open(os.path.join(target_root, "log_cycle.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return {"ok": True}
'''
    (hooks_dir / "log_hooks.py").write_text(log_hooks_py)

    # Ensure our temp project package is imported before the repo root
    monkeypatch.syspath_prepend(str(project))
    # chdir into project so persist_cycle uses project cwd for .suggestions
    cwd_before = os.getcwd()
    monkeypatch.chdir(str(project))
    try:
        # Ensure any previously-imported hooks modules are cleared so our test package is used
        import sys as _sys
        _sys.modules.pop('hooks', None)
        _sys.modules.pop('hooks.log_hooks', None)

        # Call persist_cycle with execution_mode follow_plan and an output_text that should be captured
        wiki_root = '.wiki/orchestrator'
        os.makedirs(wiki_root, exist_ok=True)
        metadata = {"execution_mode": "follow_plan", "cycle_id": "INT-CYC-1"}
        skill_usage = persist_cycle(
            wiki_root,
            prompt="Run step 1",
            user="tester",
            logging_level="full",
            output_text="This is a suggested improvement to step 1",
            dispatch_path="single-agent",
            explicit_skill_names=None,
            event_flags=None,
            metadata=metadata,
        )

        # Verify .suggestions file exists and contains the suggestion
        sugg_file = project / ".suggestions" / "suggestions.jsonl"
        assert sugg_file.exists(), "suggestions.jsonl was not created"
        lines = [l.strip() for l in sugg_file.read_text(encoding='utf-8').splitlines() if l.strip()]
        assert len(lines) >= 1
        obj = json.loads(lines[-1])
        assert obj.get("text") == "This is a suggested improvement to step 1"
        assert obj.get("cycle_id") == "INT-CYC-1"

        # Verify that our hooks.log_cycle received the ack transcript
        log_cycle_file = project / "log_cycle.json"
        assert log_cycle_file.exists()
        logged = json.loads(log_cycle_file.read_text(encoding='utf-8'))
        # The transcript should be the acknowledgement string (not the original suggestion)
        assert "Acknowledged. Continuing per plan." in (logged.get("transcript") or "")

    finally:
        monkeypatch.chdir(cwd_before)

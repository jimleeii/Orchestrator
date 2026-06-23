import json
import os
from pathlib import Path
from src.orchestrator_runtime import persist_cycle


def test_telemetry_written_on_suppression(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    hooks_dir = project / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "__init__.py").write_text("# hooks")
    (hooks_dir / "log_hooks.py").write_text("def normalize_checkpoint_metadata(summary, metadata, event_flags):\n    return metadata\n\ndef log_cycle(*a, **k):\n    return {'ok': True}\n")
    monkeypatch.syspath_prepend(str(project))
    monkeypatch.chdir(str(project))

    # monkeypatch subprocess.run to simulate processor success
    class DummyRes:
        def __init__(self):
            self.returncode = 0
            self.stdout = "ok"
            self.stderr = ""
    def fake_run(*a, **k):
        return DummyRes()
    monkeypatch.setattr('subprocess.run', fake_run)

    metadata = {"execution_mode": "follow_plan", "cycle_id": "TEL-CYC-1"}
    persist_cycle('.wiki/orchestrator', 'p', 'u', 'full', output_text='suggest me', dispatch_path='single-agent', metadata=metadata)

    telemetry_file = Path('.suggestions') / 'telemetry.jsonl'
    assert telemetry_file.exists()
    lines = [l for l in telemetry_file.read_text(encoding='utf-8').splitlines() if l.strip()]
    # should have at least two events: suppressed_suggestion and processor_run
    events = [json.loads(l) for l in lines]
    names = {e.get('event') for e in events}
    assert 'suppressed_suggestion' in names
    assert 'processor_run' in names

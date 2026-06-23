import json
import os
import tempfile
from scripts.process_suggestions import render_markdown, load_jsonl


def test_load_and_render(tmp_path):
    suggestions = [
        {"task_id": "T1", "author": "alice", "text": "Refactor X to use Y", "quality_score": 80, "step_id": "1"},
        {"task_id": "T1", "author": "bob", "text": "Add integration test for Z", "quality_score": 60, "step_id": "2"},
    ]
    jsonl = tmp_path / "s.jsonl"
    with open(jsonl, "w", encoding="utf-8") as f:
        for item in suggestions:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    loaded = load_jsonl(str(jsonl))
    assert len(loaded) == 2

    md = render_markdown("T1", loaded)
    assert "# Suggestions Evaluated — task T1" in md
    assert "Execution checklist" in md
    assert "1. Refactor X to use Y" in md
    assert "2. Add integration test for Z" in md

import threading
import json
import os
import shutil
import tempfile
from src.orchestrator_runtime import append_suggestion_entry


def test_concurrent_appends(tmp_path):
    repo_root = str(tmp_path)
    out_dir = os.path.join(repo_root, ".suggestions")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "suggestions.jsonl")

    # Prepare entries
    N = 30
    entries = [{"i": i, "text": f"suggestion-{i}"} for i in range(N)]

    def worker(e):
        append_suggestion_entry(repo_root, e)

    threads = []
    for e in entries:
        t = threading.Thread(target=worker, args=(e,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # Read lines and assert count
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    assert len(lines) == N
    loaded = [json.loads(l) for l in lines]
    texts = {item["text"] for item in loaded}
    assert texts == {f"suggestion-{i}" for i in range(N)}

import subprocess
import sys
import time
from pathlib import Path


def test_rotate_and_prune(tmp_path):
    suggestions_dir = tmp_path / ".suggestions"
    suggestions_dir.mkdir()
    suggestions_file = suggestions_dir / "suggestions.jsonl"

    # create a suggestions file larger than 1 KB
    content = "\n".join(["{\"id\": %d, \"text\": \"x\"}" % i for i in range(200)])
    suggestions_file.write_text(content, encoding="utf-8")

    # run rotate with very small max-size to force rotation
    cmd = [sys.executable, "scripts/rotate_suggestions.py", "--suggestions", str(suggestions_file), "--max-size-mb", "0", "--max-age-days", "0", "--keep-days", "1", "--keep-count", "2"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1 or res.returncode == 0

    archive = suggestions_dir / "archive"
    assert archive.exists()
    files = list(archive.glob("*.jsonl"))
    assert len(files) >= 1

    # create multiple archived files to test pruning by keep_count
    for i in range(4):
        (archive / f"suggestions-test-{i}.jsonl").write_text("{}")

    # run rotate again to trigger pruning
    res2 = subprocess.run(cmd, capture_output=True, text=True)
    assert res2.returncode in (0, 1)

    files_after = sorted(archive.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    # should be <= keep_count (2)
    assert len(files_after) <= 2

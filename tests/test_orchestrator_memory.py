from __future__ import annotations

import tempfile
import unittest
import json
import sqlite3
from pathlib import Path

from src.orchestrator_memory import (
    derive_continuity_key,
    persist_continuity_checkpoint_from_normalized_metadata,
    rebuild_continuity_store_from_records,
)


def _read_checkpoint_rows(db_path: Path) -> list[dict[str, object]]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM continuity_checkpoints ORDER BY created_at_utc ASC, id ASC"
        ).fetchall()

    result: list[dict[str, object]] = []
    for row in rows:
        payload = json.loads(row["checkpoint_json"])
        result.append({**dict(row), "checkpoint": payload})
    return result


class OrchestratorMemoryTests(unittest.TestCase):
    def test_persist_checkpoint_prefers_request_group_id_and_writes_expected_row(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_root:
            root = Path(temp_root)
            metadata = {
                "request_group_id": "grp-memory-001",
                "session_id": "session-memory-001",
                "cycle_id": "cycle-memory-001",
                "project_request": "Persist the continuity checkpoint.",
                "request_title": "Persist the continuity checkpoint.",
                "normalized_request": "persist continuity checkpoint",
                "summary": "Persist a meaningful cycle checkpoint for the continuity cache.",
                "change_applied": "Wired the derived store into the logging path.",
                "observed_result": "Continuity rows are now stored in the cache.",
                "decision": "keep",
                "next_action": "Continue the continuity rollout in the next phase.",
                "files_touched": ["src/orchestrator_memory.py", "hooks/log_hooks.py"],
            }

            persisted = persist_continuity_checkpoint_from_normalized_metadata(metadata, root=root, source_kind="test", source_identifier="unit-test")
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted["continuity_key"], "request_group:grp-memory-001")
            self.assertEqual(persisted["continuity_key_source"], "request_group_id")

            rows = _read_checkpoint_rows(root / ".wiki" / "orchestrator" / "project_memory.db")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["continuity_key"], "request_group:grp-memory-001")
            self.assertEqual(rows[0]["project_request"], "Persist the continuity checkpoint.")
            self.assertEqual(rows[0]["checkpoint"]["files_touched"], ["src/orchestrator_memory.py", "hooks/log_hooks.py"])
            self.assertEqual(rows[0]["checkpoint"]["observed_result"], "Continuity rows are now stored in the cache.")

    def test_derive_continuity_key_falls_back_to_deterministic_hash_without_request_group_id(self) -> None:
        metadata = {
            "project_request": "Rebuild the continuity store from existing artifacts.",
            "request_title": "Rebuild the continuity store from existing artifacts.",
            "normalized_request": "rebuild continuity store from existing artifacts",
            "session_id": "session-memory-002",
            "cycle_id": "cycle-memory-002",
            "workspace_id": "workspace-memory-002",
        }

        key_one = derive_continuity_key(metadata)
        key_two = derive_continuity_key({**metadata, "ignored_field": "this should not matter"})
        key_three = derive_continuity_key({**metadata, "cycle_id": "cycle-memory-003"})

        self.assertTrue(key_one.startswith("derived:"))
        self.assertEqual(key_one, key_two)
        self.assertNotEqual(key_one, key_three)

    def test_rebuild_from_records_rehydrates_store(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_root:
            root = Path(temp_root)
            records = [
                {
                    "request_group_id": "grp-rebuild-001",
                    "session_id": "session-rebuild-001",
                    "cycle_id": "cycle-rebuild-001",
                    "project_request": "Rebuild the continuity store.",
                    "change_applied": "Added the write-side persistence.",
                    "observed_result": "The cache can be regenerated.",
                    "decision": "keep",
                    "files_touched": ["src/orchestrator_memory.py"],
                },
                {
                    "project_request": "Rebuild the continuity store.",
                    "request_title": "Rebuild the continuity store.",
                    "normalized_request": "rebuild the continuity store",
                    "session_id": "session-rebuild-002",
                    "cycle_id": "cycle-rebuild-002",
                    "change_applied": "Captured the fallback hash path.",
                    "observed_result": "Derived keys remain deterministic.",
                    "next_action": "Confirm the rebuilt checkpoint contents in tests.",
                },
            ]

            count = rebuild_continuity_store_from_records(records, root=root, replace=True, source_kind="rebuild", source_identifier="unit-test")
            self.assertEqual(count, 2)

            rows = _read_checkpoint_rows(root / ".wiki" / "orchestrator" / "project_memory.db")
            self.assertEqual(len(rows), 2)
            first_row = next(row for row in rows if row["continuity_key"] == "request_group:grp-rebuild-001")
            self.assertEqual(first_row["checkpoint"]["change_applied"], "Added the write-side persistence.")

            derived_key = derive_continuity_key(records[1])
            second_row = next(row for row in rows if row["continuity_key"] == derived_key)
            self.assertEqual(second_row["checkpoint"]["next_action"], "Confirm the rebuilt checkpoint contents in tests.")


if __name__ == "__main__":
    unittest.main()

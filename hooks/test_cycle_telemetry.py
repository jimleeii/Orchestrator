from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ORCHESTRATOR_ROOT = Path(__file__).resolve().parents[1]
if str(ORCHESTRATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATOR_ROOT))

from hooks.log_hooks import log_cycle


def _telemetry_path(target_root: Path) -> Path:
    return target_root / ".wiki" / "orchestrator" / "telemetry" / "cycles.jsonl"


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_checkpoint_rows(db_path: Path) -> list[dict[str, object]]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM continuity_checkpoints ORDER BY created_at_utc ASC, id ASC"
        ).fetchall()

    return [{**dict(row), "checkpoint": json.loads(row["checkpoint_json"])} for row in rows]


class CycleTelemetryTests(unittest.TestCase):
    def test_log_cycle_writes_compact_cycle_telemetry_entry(self) -> None:
        completed = subprocess.CompletedProcess(args=["python"], returncode=0)

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_root:
            target_root = Path(temp_root)
            with mock.patch("hooks.log_hooks._run_log_command", return_value=completed):
                result = log_cycle(
                    dispatch_path="single-agent",
                    event_flags={},
                    summary="Persist compact checkpoint after successful implementation pass",
                    skills=["writing-plans"],
                    metadata={
                        "cycle_id": "cycle-compact-001",
                        "session_id": "session-compact-001",
                        "request_group_id": "grp-compact-001",
                        "project_request": "Persist compact checkpoint telemetry.",
                        "change_applied": "Wrote compact behavior and skill usage entries.",
                    },
                    target_root=target_root,
                    preview=False,
                )

            telemetry_path = _telemetry_path(target_root)
            self.assertEqual(result["command"], "/info")
            self.assertTrue(telemetry_path.exists())

            entries = _read_jsonl(telemetry_path)
            self.assertEqual(len(entries), 1)

            entry = entries[0]
            required_fields = {
                "schema_version",
                "event_type",
                "recorded_at_utc",
                "dispatch_path",
                "level",
                "command",
                "persisted",
                "preview",
                "cycle_id",
                "session_id",
                "request_group_id",
                "summary",
                "skills_used",
                "fingerprint",
            }
            self.assertTrue(required_fields.issubset(entry.keys()))
            self.assertEqual(entry["level"], "compact")
            self.assertEqual(entry["command"], "/info")
            self.assertEqual(entry["cycle_id"], "cycle-compact-001")
            self.assertEqual(entry["persisted"], True)
            self.assertIsInstance(entry["skills_used"], list)
            self.assertRegex(str(entry["fingerprint"]), r"^sha1:[0-9a-f]{40}$")

    def test_log_cycle_writes_full_cycle_telemetry_entry(self) -> None:
        completed = subprocess.CompletedProcess(args=["python"], returncode=0)

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_root:
            target_root = Path(temp_root)
            with mock.patch("hooks.log_hooks._run_log_command", return_value=completed):
                result = log_cycle(
                    dispatch_path="multi-agent",
                    event_flags={"failure_detected": True},
                    summary="Persist curated full checkpoint after multi-agent remediation",
                    skills=["systematic-debugging", "test-driven-development"],
                    metadata={
                        "curated_log": True,
                        "cycle_id": "cycle-full-001",
                        "session_id": "session-full-001",
                        "request_group_id": "grp-full-001",
                        "project_request": "Persist curated full checkpoint telemetry.",
                        "change_applied": "Recorded curated checkpoint with structured metadata.",
                        "observed_result": "Wiki and telemetry persisted in the same cycle.",
                        "decision": "keep",
                    },
                    target_root=target_root,
                    preview=False,
                )

            telemetry_path = _telemetry_path(target_root)
            self.assertEqual(result["command"], "/full-log")
            self.assertTrue(telemetry_path.exists())

            entries = _read_jsonl(telemetry_path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["level"], "full")
            self.assertEqual(entries[0]["command"], "/full-log")
            self.assertRegex(str(entries[0]["fingerprint"]), r"^sha1:[0-9a-f]{40}$")

    def test_log_cycle_writes_continuity_checkpoint_entry(self) -> None:
        completed = subprocess.CompletedProcess(args=["python"], returncode=0)

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_root:
            target_root = Path(temp_root)
            with mock.patch("hooks.log_hooks._run_log_command", return_value=completed):
                result = log_cycle(
                    dispatch_path="single-agent",
                    event_flags={},
                    summary="Persist continuity checkpoint after implementation pass",
                    skills=["writing-plans"],
                    metadata={
                        "request_group_id": "grp-continuity-001",
                        "session_id": "session-continuity-001",
                        "cycle_id": "cycle-continuity-001",
                        "project_request": "Implement the continuity store and hook integration",
                        "request_title": "Implement the continuity store and hook integration",
                        "normalized_request": "implement continuity store and hook integration",
                        "change_applied": "Wired the phase 1 store into log_cycle.",
                        "observed_result": "Continuity checkpoint persisted beside telemetry.",
                        "decision": "keep",
                        "next_action": "Add retrieval in the next phase.",
                        "files_touched": ["src/orchestrator_memory.py", "hooks/log_hooks.py"],
                    },
                    target_root=target_root,
                    preview=False,
                )

            continuity_db = target_root / ".wiki" / "orchestrator" / "project_memory.db"
            self.assertEqual(result["command"], "/info")
            self.assertTrue(continuity_db.exists())

            rows = _read_checkpoint_rows(continuity_db)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["continuity_key"], "request_group:grp-continuity-001")
            self.assertEqual(rows[0]["project_request"], "Implement the continuity store and hook integration")
            self.assertEqual(rows[0]["checkpoint"]["files_touched"], ["src/orchestrator_memory.py", "hooks/log_hooks.py"])
            self.assertEqual(rows[0]["checkpoint"]["observed_result"], "Continuity checkpoint persisted beside telemetry.")

    def test_continuity_persistence_failure_does_not_break_log_cycle(self) -> None:
        completed = subprocess.CompletedProcess(args=["python"], returncode=0)

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_root:
            target_root = Path(temp_root)
            with mock.patch("hooks.log_hooks._run_log_command", return_value=completed):
                with mock.patch(
                    "hooks.log_hooks._persist_continuity_checkpoint_from_normalized_metadata",
                    side_effect=RuntimeError("boom"),
                ):
                    result = log_cycle(
                        dispatch_path="single-agent",
                        event_flags={},
                        summary="Persist continuity checkpoint after implementation pass",
                        skills=["writing-plans"],
                        metadata={
                            "request_group_id": "grp-continuity-002",
                            "session_id": "session-continuity-002",
                            "cycle_id": "cycle-continuity-002",
                            "project_request": "Implement the continuity store and hook integration",
                            "change_applied": "Wired the phase 1 store into log_cycle.",
                            "observed_result": "Continuity checkpoint persisted beside telemetry.",
                            "decision": "keep",
                            "next_action": "Add retrieval in the next phase.",
                        },
                        target_root=target_root,
                        preview=False,
                    )

            telemetry_path = target_root / ".wiki" / "orchestrator" / "telemetry" / "cycles.jsonl"
            self.assertEqual(result["command"], "/info")
            self.assertTrue(telemetry_path.exists())

    def test_log_cycle_skipped_noise_does_not_create_cycle_telemetry(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_root:
            target_root = Path(temp_root)
            telemetry_path = _telemetry_path(target_root)

            with mock.patch("hooks.log_hooks._run_log_command") as run_log_command:
                result = log_cycle(
                    dispatch_path="multi-agent",
                    event_flags={"failure_detected": True},
                    summary="Post-tool invocation",
                    skills=None,
                    metadata={},
                    target_root=target_root,
                    preview=False,
                )

            self.assertEqual(result["action"], "skipped-noise")
            self.assertFalse(telemetry_path.exists())
            run_log_command.assert_not_called()

    def test_log_cycle_minimal_does_not_create_cycle_telemetry(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_root:
            target_root = Path(temp_root)
            telemetry_path = _telemetry_path(target_root)

            with mock.patch("hooks.log_hooks._run_log_command") as run_log_command:
                result = log_cycle(
                    dispatch_path="direct",
                    event_flags={},
                    summary="",
                    skills=None,
                    metadata={},
                    target_root=target_root,
                    preview=False,
                )

            self.assertEqual(result["level"], "minimal")
            self.assertEqual(result["action"], "none")
            self.assertFalse(telemetry_path.exists())
            run_log_command.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import io
import configparser
import json
from contextlib import redirect_stdout
from pathlib import Path


def test_dispatches_request_subcommand(monkeypatch):
    from scripts import handle_request
    from src.cli.__main__ import main

    captured = {}

    def fake_main(argv=None):
        captured["argv"] = argv
        return 11

    monkeypatch.setattr(handle_request, "main", fake_main)

    result = main(["request", "--prompt", "hello", "--user", "tester"])

    assert result == 11
    assert captured["argv"] == ["--prompt", "hello", "--user", "tester"]


def test_dispatches_package_subcommand(monkeypatch):
    import package_orchestrator
    from src.cli.__main__ import main

    captured = {}

    def fake_main(argv=None):
        captured["argv"] = argv
        return 22

    monkeypatch.setattr(package_orchestrator, "main", fake_main)

    result = main(["package", "--dry-run"])

    assert result == 22
    assert captured["argv"] == ["--dry-run"]


def test_dispatches_models_discover_subcommand(monkeypatch):
    from scripts import discover_models
    from src.cli.__main__ import main

    captured = {}

    def fake_main(argv=None):
        captured["argv"] = argv
        return 55

    monkeypatch.setattr(discover_models, "main", fake_main)

    result = main(["models", "discover", "--providers", "copilot", "--out", "catalog.json"])

    assert result == 55
    assert captured["argv"] == ["--providers", "copilot", "--out", "catalog.json"]


def test_dispatches_models_refresh_subcommand(monkeypatch):
    from scripts import refresh_model_catalog
    from src.cli.__main__ import main

    captured = {}

    def fake_main(argv=None):
        captured["argv"] = argv
        return 56

    monkeypatch.setattr(refresh_model_catalog, "main", fake_main)

    result = main(["models", "refresh", "--preview"])

    assert result == 56
    assert captured["argv"] == ["--preview"]


def test_dispatches_validate_prompts_subcommand(monkeypatch):
    from scripts import validate_prompt_mappings
    from src.cli.__main__ import main

    captured = {}

    def fake_main(argv=None):
        captured["argv"] = argv
        return 57

    monkeypatch.setattr(validate_prompt_mappings, "main", fake_main)

    result = main(["validate", "prompts", "--json"])

    assert result == 57
    assert captured["argv"] == ["--json"]


def test_dispatches_validate_api_contract_subcommand(monkeypatch):
    from scripts import validate_api_contract
    from src.cli.__main__ import main

    captured = {}

    def fake_main(argv=None):
        captured["argv"] = argv
        return 58

    monkeypatch.setattr(validate_api_contract, "main", fake_main)

    result = main(["validate", "api-contract", "--check-only"])

    assert result == 58
    assert captured["argv"] == ["--check-only"]


def test_dispatches_validate_parity_subcommand(monkeypatch):
    from scripts import check_parity
    from src.cli.__main__ import main

    captured = {}

    def fake_main(argv=None):
        captured["argv"] = argv
        return 59

    monkeypatch.setattr(check_parity, "main", fake_main)

    result = main(["validate", "parity", "--root", "."])

    assert result == 59
    assert captured["argv"] == ["--root", "."]


def test_dispatches_wiki_subcommands(monkeypatch):
    from scripts import analyze_logs, lint_wiki, normalize_log_links, search_wiki, synthesize_wiki
    from src.cli.__main__ import main

    cases = [
        (analyze_logs, ["wiki", "analyze", "--cycles", "10"], ["--cycles", "10"], 60),
        (lint_wiki, ["wiki", "lint", "--stale-days", "7"], ["--stale-days", "7"], 61),
        (search_wiki, ["wiki", "search", "term", "--wiki", ".wiki/orchestrator"], ["term", "--wiki", ".wiki/orchestrator"], 62),
        (synthesize_wiki, ["wiki", "synthesize", "--cycles", "5"], ["--cycles", "5"], 63),
        (normalize_log_links, ["wiki", "normalize-links", "--root", ".", "--dry-run"], ["--root", ".", "--dry-run"], 64),
    ]

    for module, argv, expected_argv, return_value in cases:
        captured = {}

        def fake_main(argv=None):
            captured["argv"] = argv
            return return_value

        monkeypatch.setattr(module, "main", fake_main)

        result = main(argv)

        assert result == return_value
        assert captured["argv"] == expected_argv


def test_dispatches_health_snapshot_subcommand(monkeypatch):
    import src.cli.__main__ as cli_main

    captured = {}

    class FakeSnapshot:
        def to_dict(self):
            return {
                "workspace_id": "workspace-1",
                "generated_at": "2026-06-13T12:00:00+00:00",
                "policy": {
                    "failure_threshold": 1,
                    "open_cooldown_seconds": 30,
                    "probe_cooldown_seconds": 60,
                    "probe_allowlist": [],
                    "backoff_factor": 2.0,
                    "max_backoff_seconds": 300,
                },
                "records": [
                    {
                        "scope": {
                            "workspace_id": "workspace-1",
                            "session_id": "session-1",
                            "agent_id": "Agent A",
                            "task_family": "feature",
                            "model_id": "model-1",
                        },
                        "state": {
                            "status": "closed",
                            "failure_count": 0,
                            "success_count": 3,
                            "open_until": None,
                            "probe_reserved_until": None,
                            "last_observed_at": None,
                            "last_failure_at": None,
                            "last_success_at": None,
                            "last_probe_at": None,
                            "probe_count": 0,
                            "reopen_count": 0,
                            "last_failure_kind": None,
                            "last_failure_message": None,
                        },
                    }
                ],
            }

    class FakeRegistry:
        def snapshot(self):
            captured["snapshot_called"] = True
            return FakeSnapshot()

    def fake_get_workspace_health_registry(workspace_id=None, policy=None):
        captured["workspace_id"] = workspace_id
        return FakeRegistry()

    monkeypatch.setattr(cli_main.health_monitor, "get_workspace_health_registry", fake_get_workspace_health_registry)

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = cli_main.main(["health", "snapshot", "--workspace-id", "workspace-1", "--json"])

    assert result == 0
    assert captured["workspace_id"] == "workspace-1"
    assert captured["snapshot_called"] is True
    payload = json.loads(buffer.getvalue())
    assert payload["workspace_id"] == "workspace-1"
    assert payload["records"][0]["scope"]["agent_id"] == "Agent A"


def test_dispatches_health_route_subcommand(monkeypatch):
    import src.cli.__main__ as cli_main

    captured = {}

    class FakeScope:
        def __init__(self, workspace_id, session_id, task_family, model_id):
            self.workspace_id = workspace_id
            self.session_id = session_id
            self.task_family = task_family
            self.model_id = model_id

    class FakeDecision:
        def to_dict(self):
            return {
                "workspace_id": "workspace-2",
                "session_id": "session-2",
                "task_family": "feature",
                "state": "half-open",
                "action": "probe",
                "reason": "probe candidate selected after all closed candidates were suppressed",
                "selected_candidates": ["Agent A"],
                "suppressed_candidates": ["Agent B"],
                "probe_candidate": "Agent A",
                "model_id": "model-9",
            }

    class FakeRegistry:
        def route_candidates(self, candidates, *, session_id, task_family, model_id, probe_allowlist=None, now=None):
            captured["route_args"] = (candidates, session_id, task_family, model_id)
            return FakeDecision()

    def fake_build_health_scope(metadata, agent_id, *, dispatch_type=None, workspace_id=None):
        captured["scope_args"] = (metadata, agent_id, dispatch_type, workspace_id)
        return FakeScope("workspace-2", "session-2", "feature", "model-9")

    def fake_get_workspace_health_registry(workspace_id=None, policy=None):
        captured["registry_workspace_id"] = workspace_id
        return FakeRegistry()

    monkeypatch.setattr(cli_main.health_monitor, "build_health_scope", fake_build_health_scope)
    monkeypatch.setattr(cli_main.health_monitor, "get_workspace_health_registry", fake_get_workspace_health_registry)

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = cli_main.main([
            "health",
            "route",
            "Agent A",
            "Agent B",
            "--workspace-id",
            "workspace-2",
            "--session-id",
            "session-2",
            "--task-family",
            "feature",
            "--model-id",
            "model-9",
            "--json",
        ])

    assert result == 0
    assert captured["registry_workspace_id"] == "workspace-2"
    assert captured["scope_args"][0]["workspace_id"] == "workspace-2"
    assert captured["route_args"] == (["Agent A", "Agent B"], "session-2", "feature", "model-9")
    payload = json.loads(buffer.getvalue())
    assert payload["action"] == "probe"
    assert payload["selected_candidates"] == ["Agent A"]


def test_dispatches_log_subcommand_to_log_prompt(monkeypatch):
    from scripts import log_prompt
    from src.cli.__main__ import main

    captured = {}

    def fake_main(argv=None):
        captured["argv"] = argv
        return 33

    monkeypatch.setattr(log_prompt, "main", fake_main)

    result = main(["log", "full-log", "--preview", "--author", "tester"])

    assert result == 33
    assert captured["argv"] == ["/full-log", "--preview", "--author", "tester"]


def test_dispatches_log_cleanup_level(monkeypatch):
    from scripts import log_prompt
    from src.cli.__main__ import main

    captured = {}

    def fake_main(argv=None):
        captured["argv"] = argv
        return 44

    monkeypatch.setattr(log_prompt, "main", fake_main)

    result = main(["log", "cleanup", "--manifest"])

    assert result == 44
    assert captured["argv"] == ["/cleanup", "--manifest"]


def test_setup_cfg_exposes_top_level_orchestrator_entry_point():
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(Path(__file__).resolve().parents[1] / "setup.cfg", encoding="utf-8")

    entry_points = dict(
        line.split(" = ", 1)
        for line in config["options.entry_points"]["console_scripts"].splitlines()
        if line.strip()
    )

    assert entry_points["orchestrator"] == "src.cli.__main__:main"
    assert entry_points["orchestrator-handle-request"] == "scripts.handle_request:main"
    assert entry_points["orchestrator-package"] == "package_orchestrator:main"
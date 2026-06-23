from scripts.metrics_server import telemetry_to_prom
import json

def test_event_type_and_severity_labels(tmp_path):
    telemetry = tmp_path / "telemetry.json"
    data = {
        "events": {"suppressed": 5, "structured": 2},
        "items": {
            "taskA": {"count": 3, "severity": "high"},
            "taskB": {"count": 1, "severity": "low"}
        },
        "cycles": 3
    }
    telemetry.write_text(json.dumps(data), encoding="utf-8")
    prom = telemetry_to_prom(str(telemetry))
    # should include event_type labels for events
    assert 'event_type="suppressed"' in prom
    assert 'event_type="structured"' in prom
    # should include severity labels for items
    assert 'severity="high"' in prom
    assert 'severity="low"' in prom
    # cycles numeric
    assert "orchestrator_telemetry_cycles" in prom

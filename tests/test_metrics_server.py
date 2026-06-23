import subprocess
import sys
import time
import os
import urllib.request


def test_metrics_server_smoke(tmp_path):
    # prepare a temporary metrics file
    metrics_file = tmp_path / "metrics.prom"
    sample = "# HELP test_counter A test counter\n# TYPE test_counter counter\ntest_counter 42\n"
    metrics_file.write_text(sample, encoding="utf-8")

    port = 8001
    cmd = [sys.executable, os.path.join("scripts", "metrics_server.py"), "--port", str(port), "--metrics-file", str(metrics_file)]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        # wait briefly for server to start
        time.sleep(0.5)

        # GET /metrics
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=5) as r:
            body = r.read().decode("utf-8")
        assert "test_counter 42" in body

        # GET /health
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as r:
            health = r.read().decode("utf-8")
        assert health == "ok"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
    # also test telemetry conversion works when telemetry_summary.json exists
    telemetry = tmp_path / "telemetry_summary.json"
    telemetry.write_text('{"events": {"suppressed": 5, "structured": 2}, "cycles": 3}', encoding="utf-8")
    port2 = port + 1
    cmd2 = [sys.executable, os.path.join("scripts", "metrics_server.py"), "--port", str(port2), "--metrics-file", str(metrics_file)]
    proc2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(0.5)
        with urllib.request.urlopen(f"http://127.0.0.1:{port2}/metrics", timeout=5) as r:
            body = r.read().decode("utf-8")
        assert "orchestrator_telemetry" in body
    finally:
        proc2.terminate()
        try:
            proc2.wait(timeout=3)
        except Exception:
            proc2.kill()
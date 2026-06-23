#!/usr/bin/env python3
"""
Simple metrics HTTP server for Prometheus scraping.

This server serves the contents of a metrics file (default: .suggestions/metrics.prom)
at the /metrics endpoint. It is intentionally dependency-free (uses Python stdlib)
so it can be run in most environments without adding packages.

Usage:
  python scripts/metrics_server.py --port 8000 --metrics-file .suggestions/metrics.prom
  python scripts/metrics_server.py --once --metrics-file .suggestions/metrics.prom

"""
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import argparse
import os
import sys
import json


class MetricsHandler(BaseHTTPRequestHandler):
    def __init__(self, metrics_path, *args, **kwargs):
        self._metrics_path = metrics_path
        super().__init__(*args, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/metrics":
            self._serve_metrics()
            return
        if parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        self.send_response(404)
        self.end_headers()

    def _serve_metrics(self):
        try:
            # Prefer dynamic telemetry_summary.json if present
            telemetry_path = os.path.join(os.path.dirname(self._metrics_path), "telemetry_summary.json")
            if os.path.exists(telemetry_path):
                prom = telemetry_to_prom(telemetry_path)
                data = prom.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            # Fallback to static metrics file
            if not os.path.exists(self._metrics_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"")
                return

            with open(self._metrics_path, "rb") as f:
                data = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.send_response(500)
            self.end_headers()


def telemetry_to_prom(telemetry_path):
    """Read telemetry_summary.json and convert to Prometheus text format.

    The function flattens numeric values and simple dicts into metrics.
    Nested dicts are represented as labels with key names preserved.
    """
    try:
        with open(telemetry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return ""

    lines = []
    emitted_metrics = set()

    def emit_metric(name, value, labels=None):
        metric = sanitize_metric_name(name)
        # help/type comments (emit once per metric)
        if metric not in emitted_metrics:
            lines.append(f"# HELP {metric} Orchestrator telemetry metric {metric}")
            lines.append(f"# TYPE {metric} gauge")
            emitted_metrics.add(metric)

        label_str = ""
        if labels:
            parts = [f'{k}="{v}"' for k, v in labels.items()]
            label_str = "{" + ",".join(parts) + "}"
        # ensure numeric formatting for booleans
        if isinstance(value, bool):
            value = 1 if value else 0
        lines.append(f"{metric}{label_str} {value}")

    def walk(prefix, obj):
        if isinstance(obj, (int, float)):
            emit_metric(prefix, obj)
            return
        if isinstance(obj, dict):
            # If dict values are numeric, emit metrics with label
            all_numeric = all(isinstance(v, (int, float)) for v in obj.values())
            if all_numeric:
                # prefer semantic label names for known prefixes
                label_name = "key"
                if prefix.endswith("events") or prefix == "events":
                    label_name = "event_type"
                for k, v in obj.items():
                    emit_metric(prefix, v, labels={label_name: str(k)})
                return

            # handle dicts whose values are dicts with counts and optional severity
            handled = False
            for k, v in obj.items():
                if isinstance(v, dict) and ("count" in v or "severity" in v):
                    cnt = v.get("count")
                    if isinstance(cnt, (int, float)):
                        labels = {}
                        if "severity" in v:
                            labels["severity"] = str(v.get("severity"))
                        # use the key as an event_type if prefix suggests events
                        if prefix.endswith("events") or prefix == "events":
                            labels.setdefault("event_type", str(k))
                        emit_metric(f"{prefix}", cnt, labels=labels)
                        handled = True
                    else:
                        # recurse into nested structure
                        walk(f"{prefix}_{k}", v)
                else:
                    # recurse for general nested structures
                    walk(f"{prefix}_{k}", v)
            if handled:
                return
            # otherwise, recurse normally
            return
            return
        # lists: emit length and optionally numeric contents
        if isinstance(obj, list):
            emit_metric(f"{prefix}_count", len(obj))
            return
        # fallback: ignore

    def sanitize_metric_name(n: str) -> str:
        # replace non-alphanum with underscore and ensure prefix
        safe = []
        for ch in n:
            # Prometheus metric names should match [a-zA-Z_:][a-zA-Z0-9_:]*
            if ch.isalnum() or ch == "_":
                safe.append(ch)
            else:
                safe.append("_")
        body = "".join(safe).strip("_")
        # ensure it starts with a letter or underscore
        if not body or not (body[0].isalpha() or body[0] == "_"):
            body = "m_" + body
        metric = "orchestrator_telemetry_" + body
        return metric

    # Walk top-level keys
    for key, val in data.items():
        walk(key, val)

    # add a timestamp metric for last update
    try:
        mtime = os.path.getmtime(telemetry_path)
        lines.append(f"orchestrator_telemetry_last_update {int(mtime)}")
    except Exception:
        pass

    return "\n".join(lines) + "\n"


def make_handler(metrics_path):
    def handler(*args, **kwargs):
        MetricsHandler(metrics_path, *args, **kwargs)

    return handler


def main(argv=None):
    parser = argparse.ArgumentParser(description="Serve Prometheus metrics from a file")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--metrics-file", default=".suggestions/metrics.prom", help="Metrics file path to serve")
    parser.add_argument("--once", action="store_true", help="Print metrics to stdout once and exit")
    args = parser.parse_args(argv)

    metrics_path = os.path.abspath(args.metrics_file)

    if args.once:
        if os.path.exists(metrics_path):
            with open(metrics_path, "r", encoding="utf-8") as f:
                print(f.read())
        else:
            # no metrics yet, exit quietly
            print("", end="")
        return 0

    server_address = ("0.0.0.0", args.port)
    handler = make_handler(metrics_path)
    httpd = HTTPServer(server_address, handler)
    print(f"Metrics server listening on http://{server_address[0]}:{server_address[1]}/metrics")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("shutting down")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    sys.exit(main())

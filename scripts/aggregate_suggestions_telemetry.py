"""Aggregate suggestion telemetry into a summary JSON and Prometheus text file.

Usage: python scripts/aggregate_suggestions_telemetry.py --root <repo_root>

Reads: <root>/.suggestions/telemetry.jsonl
Writes: <root>/.suggestions/telemetry_summary.json
        <root>/.suggestions/metrics.prom

The Prometheus text file contains simple counters for event types and a gauge for
last_processed_unix_timestamp.
"""
import argparse
import json
import os
import time
from collections import Counter, defaultdict


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                # skip malformed lines
                continue
    return items


def summarize(events):
    counts = Counter()
    by_cycle = defaultdict(Counter)
    last_ts = None
    for e in events:
        evt = e.get("event") or "unknown"
        counts[evt] += 1
        cid = e.get("cycle_id") or e.get("task_id") or "-"
        by_cycle[cid][evt] += 1
        ts = e.get("timestamp")
        if ts:
            try:
                # ISO8601-ish, compare lexicographically
                if last_ts is None or ts > last_ts:
                    last_ts = ts
            except Exception:
                pass
    return {"counts": dict(counts), "by_cycle": {k: dict(v) for k, v in by_cycle.items()}, "last_timestamp": last_ts}


def write_summary(root, summary):
    out_dir = os.path.join(root, ".suggestions")
    os.makedirs(out_dir, exist_ok=True)
    out_json = os.path.join(out_dir, "telemetry_summary.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    # also write prometheus-style metrics
    prom = []
    for k, v in summary.get("counts", {}).items():
        name = k.replace("-", "_")
        prom.append(f"suggestions_{{event=\"{k}\"}} {v}")
    # gauge for last processed timestamp
    last_ts = summary.get("last_timestamp")
    if last_ts:
        try:
            # best-effort: write unix timestamp
            # attempt to parse ISO timestamp to unix epoch
            # fallback to current time
            import datetime
            try:
                dt = datetime.datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                unix = int(dt.timestamp())
            except Exception:
                unix = int(time.time())
        except Exception:
            unix = int(time.time())
    else:
        unix = int(time.time())
    prom.append(f"suggestions_last_processed_unix {unix}")
    out_prom = os.path.join(out_dir, "metrics.prom")
    with open(out_prom, "w", encoding="utf-8") as f:
        f.write("\n".join(prom) + "\n")
    return out_json, out_prom


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", "-r", default=".")
    args = p.parse_args()
    root = args.root
    path = os.path.join(root, ".suggestions", "telemetry.jsonl")
    events = load_jsonl(path)
    summary = summarize(events)
    out_json, out_prom = write_summary(root, summary)
    print(f"Wrote summary: {out_json}")
    print(f"Wrote prometheus metrics: {out_prom}")


if __name__ == "__main__":
    main()

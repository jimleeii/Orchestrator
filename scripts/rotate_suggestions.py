#!/usr/bin/env python3
"""
Rotate and prune .suggestions/suggestions.jsonl based on size or age.

Usage:
  python scripts/rotate_suggestions.py --suggestions .suggestions/suggestions.jsonl \
      --max-size-mb 10 --max-age-days 30 --keep-days 90 --keep-count 10

"""
import argparse
import os
import shutil
import time
from datetime import datetime, timedelta


def rotate_if_needed(path, max_size_mb, max_age_days, keep_days, keep_count):
    if not os.path.exists(path):
        return 0

    size = os.path.getsize(path)
    mtime = os.path.getmtime(path)
    now = time.time()

    need_rotate = False
    if max_size_mb is not None and size > max_size_mb * 1024 * 1024:
        need_rotate = True
    if max_age_days is not None and (now - mtime) > (max_age_days * 86400):
        need_rotate = True

    archive_dir = os.path.join(os.path.dirname(path), "archive")
    os.makedirs(archive_dir, exist_ok=True)

    if need_rotate:
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        dest = os.path.join(archive_dir, f"suggestions-{ts}.jsonl")
        shutil.move(path, dest)
        # create a new empty suggestions file
        open(path, "w", encoding="utf-8").close()

    # prune archives by age and count
    files = [os.path.join(archive_dir, f) for f in os.listdir(archive_dir) if f.endswith(".jsonl")]
    files = sorted(files, key=lambda p: os.path.getmtime(p))

    # remove older than keep_days
    if keep_days is not None:
        cutoff = time.time() - (keep_days * 86400)
        for f in files:
            if os.path.getmtime(f) < cutoff:
                try:
                    os.remove(f)
                except Exception:
                    pass

    # enforce keep_count
    files = [os.path.join(archive_dir, f) for f in os.listdir(archive_dir) if f.endswith(".jsonl")]
    files = sorted(files, key=lambda p: os.path.getmtime(p))
    while keep_count is not None and len(files) > keep_count:
        f = files.pop(0)
        try:
            os.remove(f)
        except Exception:
            pass

    return 1 if need_rotate else 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--suggestions", default=".suggestions/suggestions.jsonl")
    parser.add_argument("--max-size-mb", type=int, default=10)
    parser.add_argument("--max-age-days", type=int, default=30)
    parser.add_argument("--keep-days", type=int, default=90)
    parser.add_argument("--keep-count", type=int, default=10)
    args = parser.parse_args(argv)

    rc = rotate_if_needed(args.suggestions, args.max_size_mb, args.max_age_days, args.keep_days, args.keep_count)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

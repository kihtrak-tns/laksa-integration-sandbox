#!/usr/bin/env python3
"""Offline first-pass summary of a stopped ROS 2 SQLite bag; no ROS install needed."""

import argparse
import json
from pathlib import Path
import sqlite3


def summarize(folder):
    bag = folder / "bag"
    if not (bag / "metadata.yaml").is_file():
        raise ValueError("metadata.yaml missing; stop/finalize recorder and copy entire directory")
    files = sorted(bag.glob("*.db3"))
    if not files:
        raise ValueError("no SQLite .db3 files found")
    totals = {}
    for path in files:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            query = """SELECT topics.name, COUNT(*), MIN(messages.timestamp), MAX(messages.timestamp)
                       FROM messages JOIN topics ON messages.topic_id = topics.id
                       GROUP BY topics.name"""
            for name, count, first, last in con.execute(query):
                entry = totals.setdefault(name, {"messages": 0, "first_ns": first, "last_ns": last})
                entry["messages"] += count
                entry["first_ns"] = min(entry["first_ns"], first)
                entry["last_ns"] = max(entry["last_ns"], last)
        finally:
            con.close()
    for name, entry in totals.items():
        span = (entry["last_ns"] - entry["first_ns"]) / 1e9
        entry["span_sec"] = round(span, 2)
        entry["average_hz"] = round((entry["messages"] - 1) / span, 2) if span > 0 else None
    events_file = folder / "events.jsonl"
    events = [json.loads(line) for line in events_file.read_text().splitlines()] if events_file.exists() else []
    missing = [topic for topic in ("/scan", "/laksa/state", "/laksa/vesc/state", "/laksa/command")
               if topic not in totals]
    return {"run": folder.name, "files": [p.name for p in files], "topics": totals,
            "missing_core_topics": missing, "events": events}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="the run directory copied from the Orin")
    args = parser.parse_args()
    print(json.dumps(summarize(args.run.expanduser()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

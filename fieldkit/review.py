#!/usr/bin/env python3
"""Offline first-pass summary of a stopped ROS 2 SQLite bag; no ROS install needed."""

import argparse
import json
from pathlib import Path
import sqlite3

GAP_TOPICS = {"/scan", "/scan_raw", "/laksa/lidar/scan_validated", "/laksa/state",
              "/laksa/vesc/state", "/laksa/imu/data", "/laksa/command",
              "/laksa/odometry/fused", "/laksa/odom", "/zed/zed_node/odom"}


def summarize(folder):
    bag = folder / "bag"
    if not (bag / "metadata.yaml").is_file():
        raise ValueError("metadata.yaml missing; stop/finalize recorder and copy entire directory")
    files = sorted(bag.glob("*.db3"))
    if not files:
        raise ValueError("no SQLite .db3 files found")
    totals = {}
    intervals = {}
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
                if name in GAP_TOPICS:
                    previous = None
                    largest_gap = 0
                    for (timestamp,) in con.execute(
                        "SELECT messages.timestamp FROM messages JOIN topics ON messages.topic_id=topics.id "
                        "WHERE topics.name=? ORDER BY messages.timestamp", (name,)
                    ):
                        if previous is not None:
                            largest_gap = max(largest_gap, timestamp - previous)
                        previous = timestamp
                    intervals.setdefault(name, []).append((first, last, largest_gap))
        finally:
            con.close()
    for name, entry in totals.items():
        span = (entry["last_ns"] - entry["first_ns"]) / 1e9
        entry["span_sec"] = round(span, 2)
        entry["average_hz"] = round((entry["messages"] - 1) / span, 2) if span > 0 else None
        if name in intervals:
            ordered = sorted(intervals[name])
            max_gap = max(item[2] for item in ordered)
            for left, right in zip(ordered, ordered[1:]):
                max_gap = max(max_gap, right[0] - left[1])
            entry["largest_receipt_gap_sec"] = round(max_gap / 1e9, 4)
    events_file = folder / "events.jsonl"
    events = [json.loads(line) for line in events_file.read_text().splitlines()] if events_file.exists() else []
    missing = [topic for topic in ("/scan", "/tf_static", "/laksa/state", "/laksa/vesc/state", "/laksa/command")
               if topic not in totals]
    selected_file = folder / "topics_at_start.json"
    selected = json.loads(selected_file.read_text()).get("selected", []) if selected_file.exists() else []
    empty = [topic for topic in selected if topic not in totals]
    return {"run": folder.name, "files": [p.name for p in files], "topics": totals,
            "missing_core_topics": missing, "selected_topics_with_no_messages": empty,
            "recon_scan_and_static_tf_present": all(topic in totals for topic in ("/scan", "/tf_static")),
            "gap_note": "Gaps are bag receipt time, not sensor acquisition time; they flag evidence to inspect, not a diagnosed cause.",
            "events": events}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="the run directory copied from the Orin")
    args = parser.parse_args()
    print(json.dumps(summarize(args.run.expanduser()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

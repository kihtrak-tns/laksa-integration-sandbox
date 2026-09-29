"""Extract only serialized ``/scan`` records from a ROS 2 SQLite bag.

Run on the ROS 2 Humble host that has the original bag. CDR payloads and bag
timestamps are copied unchanged; this module never deserializes or rewrites a
LaserScan field.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Callable, Iterable


SCAN_TOPIC = "/scan"
SCAN_TYPE = "sensor_msgs/msg/LaserScan"


def scan_topic_metadata(topics: Iterable[object]) -> object:
    matches = [topic for topic in topics if getattr(topic, "name", None) == SCAN_TOPIC]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {SCAN_TOPIC} topic, found {len(matches)}")
    if getattr(matches[0], "type", None) != SCAN_TYPE:
        raise ValueError(f"{SCAN_TOPIC} has type {getattr(matches[0], 'type', None)!r}, expected {SCAN_TYPE}")
    return matches[0]


def copy_scan_records(
    records: Iterable[tuple[str, bytes, int]],
    write_record: Callable[[str, bytes, int], None],
) -> tuple[int, int | None, int | None]:
    """Copy only /scan CDR records while preserving payload bytes and time."""
    count = 0
    first_stamp = None
    last_stamp = None
    for topic, payload, stamp_ns in records:
        if topic != SCAN_TOPIC:
            continue
        write_record(topic, payload, stamp_ns)
        stamp_ns = int(stamp_ns)
        if first_stamp is None:
            first_stamp = stamp_ns
        last_stamp = stamp_ns
        count += 1
    return count, first_stamp, last_stamp


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_scan_bag(source: Path, output: Path) -> dict:
    import rosbag2_py

    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    source_metadata = source / "metadata.yaml"
    if not source_metadata.is_file():
        raise FileNotFoundError(f"source bag metadata not found: {source_metadata}")

    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=str(source), storage_id="sqlite3"),
        rosbag2_py.ConverterOptions(input_serialization_format="cdr", output_serialization_format="cdr"),
    )
    topic_metadata = scan_topic_metadata(reader.get_all_topics_and_types())
    if topic_metadata.serialization_format != "cdr":
        raise ValueError(f"expected CDR /scan, got {topic_metadata.serialization_format!r}")
    reader.set_filter(rosbag2_py.StorageFilter(topics=[SCAN_TOPIC]))

    output.mkdir(parents=False)
    writer = rosbag2_py.SequentialWriter()
    writer_open = False
    try:
        writer.open(
            rosbag2_py.StorageOptions(uri=str(output), storage_id="sqlite3"),
            rosbag2_py.ConverterOptions(input_serialization_format="cdr", output_serialization_format="cdr"),
        )
        writer_open = True
        writer.create_topic(topic_metadata)

        def records():
            while reader.has_next():
                yield reader.read_next()

        count, first_stamp, last_stamp = copy_scan_records(
            records(), lambda topic, payload, stamp: writer.write(topic, payload, stamp)
        )
    finally:
        if writer_open:
            writer.close()
        del reader
    if count == 0:
        raise ValueError("source bag contains no /scan messages")

    source_files = [
        {"name": item.name, "bytes": item.stat().st_size}
        for item in sorted(source.glob("*.db3"))
    ]
    identity = {
        "schema": "laksa-scan-only-export-v1",
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_bag_uri": str(source),
        "source_metadata_sha256": _sha256(source_metadata),
        "source_storage_files": source_files,
        "topic": SCAN_TOPIC,
        "type": SCAN_TYPE,
        "serialization_format": topic_metadata.serialization_format,
        "record_count": count,
        "first_bag_timestamp_ns": first_stamp,
        "last_bag_timestamp_ns": last_stamp,
        "cdr_payloads_copied_verbatim": True,
        "header_and_ranges_preserved_by_serialized_copy": True,
    }
    (output / "source_identity.json").write_text(
        json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return identity


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_bag", type=Path)
    parser.add_argument("output_bag", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(export_scan_bag(args.source_bag, args.output_bag), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

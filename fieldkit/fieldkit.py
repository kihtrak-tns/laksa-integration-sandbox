#!/usr/bin/env python3
"""Offline, read-only LAKSA ROS 2 field recorder for the Orin (Python 3.10+)."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time


TOPICS = (
    "/scan", "/scan_raw", "/laksa/lidar/scan_validated", "/tf", "/tf_static",
    "/laksa/state", "/laksa/vesc/state", "/laksa/imu/data", "/laksa/battery_state",
    "/laksa/command", "/laksa/autonomy_candidate_command", "/laksa/brake",
    "/laksa/odometry/fused", "/laksa/odom", "/zed/zed_node/odom",
    "/laksa/nav_cmd_vel", "/laksa/mission_state", "/laksa/autonomy_health",
    "/laksa/health/summary", "/diagnostics", "/laksa/emergency_stop",
    "/laksa/emergency_stop_reason", "/laksa/autonomous_enabled",
    "/laksa/exploration_enabled", "/laksa/mapping/state", "/map",
    "/c1/drive_request", "/c1/odom", "/c1/rpp_feasibility",
    "/c1/controller_feasibility", "/c1/nav2_cmd_vel",
)
DEFAULT_ROOT = Path.home() / "laksa_field_runs"
NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,55}$")
TOPIC_RE = re.compile(r"^(/\S+)\s+\[([^]]+)\]$")


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def environment(setups):
    for setup in setups:
        if not Path(setup).expanduser().is_file():
            raise RuntimeError(f"ROS setup missing: {setup}")
    command = "set -e; " + "; ".join(
        "source " + shlex.quote(str(Path(s).expanduser())) for s in setups
    ) + "; env -0"
    data = subprocess.check_output(["bash", "-c", command], timeout=20)
    return dict(part.decode().split("=", 1) for part in data.split(b"\0") if part)


def run(command, env=None, timeout=15):
    try:
        proc = subprocess.run(command, env=env, capture_output=True, text=True,
                              timeout=timeout, check=False)
        return {"command": command, "exit_code": proc.returncode,
                "stdout": proc.stdout, "stderr": proc.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": command, "exit_code": -1, "stdout": "", "stderr": str(exc)}


def discover(env):
    result = run(["ros2", "topic", "list", "-t"], env, timeout=20)
    if result["exit_code"]:
        raise RuntimeError("ROS topic discovery failed: " + result["stderr"])
    seen = {}
    for line in result["stdout"].splitlines():
        match = TOPIC_RE.match(line.strip())
        if match:
            seen.setdefault(match.group(1), []).append(match.group(2))
    selected = [topic for topic in TOPICS if len(seen.get(topic, [])) == 1]
    return result, seen, selected


def snapshot(folder, env, git_dir=None):
    checks = {
        "utc": stamp(), "host": run(["hostname"]),
        "kernel": run(["uname", "-a"]), "disk": run(["df", "-h", str(folder)]),
        "lsusb": run(["lsusb"]), "network": run(["ip", "-brief", "address"]),
        "nodes": run(["ros2", "node", "list"], env, 20),
        "topics": run(["ros2", "topic", "list", "-t"], env, 20),
        "ros_domain_id": env.get("ROS_DOMAIN_ID", "0"),
        "rmw_implementation": env.get("RMW_IMPLEMENTATION", "default"),
        "command_endpoints": run(["ros2", "topic", "info", "/laksa/command", "--verbose"], env, 10),
        "static_tf_endpoints": run(["ros2", "topic", "info", "/tf_static", "--verbose"], env, 10),
        "scan_endpoints": run(["ros2", "topic", "info", "/scan", "--verbose"], env, 10),
        "scan_header": run(["ros2", "topic", "echo", "/scan", "--once", "--field", "header",
                            "--qos-reliability", "best_effort"], env, 4),
        "static_tf_sample": run(["ros2", "topic", "echo", "/tf_static", "--once",
                                 "--qos-durability", "transient_local", "--qos-reliability", "reliable"], env, 4),
        "vesc_sample": run(["ros2", "topic", "echo", "/laksa/vesc/state", "--once",
                            "--qos-reliability", "best_effort"], env, 4),
    }
    counts = Counter(checks["nodes"]["stdout"].splitlines())
    checks["duplicate_node_names"] = [name for name, count in counts.items() if count > 1]
    if git_dir:
        checks["git_head"] = run(["git", "-C", str(git_dir), "rev-parse", "HEAD"])
        checks["git_status"] = run(["git", "-C", str(git_dir), "status", "--short"])
    write_json(folder / "snapshot.json", checks)
    return checks


def state_path(folder):
    return folder / "recorder.json"


def pid_is_recorder(pid, folder):
    try:
        cmdline = (Path("/proc") / str(pid) / "cmdline").read_bytes().replace(b"\0", b" ")
        return b"ros2 bag record" in cmdline and str(folder / "bag").encode() in cmdline
    except OSError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--setup", action="append", default=[],
                        help="additional workspace install/setup.bash; may be repeated")
    sub = parser.add_subparsers(dest="action", required=True)
    pre = sub.add_parser("preflight")
    pre.add_argument("--git-dir", type=Path)
    start = sub.add_parser("start")
    start.add_argument("name", help="unique visit/run label, e.g. night1-obstacle")
    start.add_argument("--git-dir", type=Path)
    start.add_argument("--min-free-gb", type=float, default=4)
    start.add_argument("--dry-run", action="store_true")
    for action in ("mark", "stop", "report"):
        cmd = sub.add_parser(action)
        cmd.add_argument("name")
        if action == "mark":
            cmd.add_argument("note", help="short event; include observed course position")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if args.action == "preflight":
        root.mkdir(parents=True, exist_ok=True)
        env = environment(["/opt/ros/humble/setup.bash"] + args.setup)
        result, seen, selected = discover(env)
        checks = snapshot(root, env, args.git_dir)
        print("Detected", len(seen), "topics; selected", len(selected), "for recording:")
        print("\n".join(selected))
        print("Missing core topics:", ", ".join(t for t in ("/scan", "/laksa/state", "/laksa/vesc/state") if t not in selected) or "none")
        print("Available GiB:", round(shutil.disk_usage(root).free / 2**30, 2))
        match = re.search(r"Publisher count:\s*(\d+)", checks["command_endpoints"]["stdout"])
        print("/laksa/command publisher count:", match.group(1) if match else "unknown; inspect snapshot.json")
        print("Duplicate node names:", checks["duplicate_node_names"] or "none reported")
        if "/tf_static" not in selected:
            print("WARNING: /tf_static not found. Save measured sensor mounting and frame names; do not invent transforms.")
        return
    if not NAME_RE.fullmatch(args.name):
        parser.error("name must be 1-56 letters, digits, hyphens or underscores")
    folder = root / args.name
    if args.action == "start":
        if folder.exists():
            parser.error(f"run already exists: {folder}")
        root.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(root).free / 2**30
        if free < args.min_free_gb:
            parser.error(f"only {free:.2f} GiB free; requires {args.min_free_gb} GiB")
        env = environment(["/opt/ros/humble/setup.bash"] + args.setup)
        _, seen, selected = discover(env)
        if not selected or "/scan" not in selected:
            parser.error("no /scan discovered; check ROS graph and setup before recording")
        if args.dry_run:
            print("Would record:", " ".join(selected))
            return
        folder.mkdir()
        snapshot(folder, env, args.git_dir)
        write_json(folder / "topics_at_start.json", {"available": seen, "selected": selected})
        # Request historical static transforms from transient-local publishers.
        qos_path = folder / "record_qos.yaml"
        qos_path.write_text("/tf_static:\n  reliability: reliable\n  durability: transient_local\n  history: keep_last\n  depth: 100\n")
        log = (folder / "recorder.log").open("w")
        try:
            proc = subprocess.Popen(["ros2", "bag", "record", "-s", "sqlite3", "-o", str(folder / "bag"),
                                     "--qos-profile-overrides-path", str(qos_path), *selected],
                                    env=env, stdin=subprocess.DEVNULL, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
        finally:
            log.close()
        write_json(state_path(folder), {"pid": proc.pid, "started_utc": stamp(),
                                       "selected": selected, "bag": str(folder / "bag")})
        (folder / "events.jsonl").open("a").write(json.dumps({"utc": stamp(), "event": "START"}) + "\n")
        time.sleep(2)
        if proc.poll() is not None:
            raise RuntimeError(f"recorder exited ({proc.returncode}); inspect {folder / 'recorder.log'}")
        print(f"Recording locally: {folder}; PID {proc.pid}. Stop with: fieldkit.py --root {root} stop {args.name}")
        return
    if not folder.is_dir():
        parser.error(f"run not found: {folder}")
    if args.action == "mark":
        with (folder / "events.jsonl").open("a") as out:
            out.write(json.dumps({"utc": stamp(), "monotonic_ns": time.monotonic_ns(),
                                  "event": args.note}) + "\n")
        print("Marked", args.name, args.note)
        return
    state = json.loads(state_path(folder).read_text())
    if args.action == "stop":
        pid = state["pid"]
        if not pid_is_recorder(pid, folder):
            parser.error("recording process no longer matches; inspect bag and log manually")
        os.killpg(pid, signal.SIGINT)
        for _ in range(30):
            if not pid_is_recorder(pid, folder):
                break
            time.sleep(0.5)
        if pid_is_recorder(pid, folder):
            raise RuntimeError("recorder has not finalized after 15 s; inspect its log and stop it before copying the bag")
        with (folder / "events.jsonl").open("a") as out:
            out.write(json.dumps({"utc": stamp(), "event": "STOP_REQUESTED"}) + "\n")
        write_json(folder / "postflight.json", {
            "utc": stamp(), "bag_info": run(["ros2", "bag", "info", str(folder / "bag")],
                                           environment(["/opt/ros/humble/setup.bash"] + args.setup), 25),
            "disk": run(["df", "-h", str(folder)]),
            "kernel_recent": run(["journalctl", "-k", "-b", "--since", state["started_utc"], "--no-pager"], timeout=20),
            "agent_events": run(["journalctl", "-b", "--since", state["started_utc"],
                                 "--no-pager", "--grep", "micro_ros|Micro XRCE|create_client|delete_client|destroy_session|ttyACM"], timeout=20),
        })
        print("Stopped; inspect", folder / "postflight.json", "and", folder / "recorder.log")
        return
    print(json.dumps({"state": state, "bag_exists": (folder / "bag" / "metadata.yaml").exists(),
                      "recorder_alive": pid_is_recorder(state["pid"], folder),
                      "events": (folder / "events.jsonl").read_text().splitlines()}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

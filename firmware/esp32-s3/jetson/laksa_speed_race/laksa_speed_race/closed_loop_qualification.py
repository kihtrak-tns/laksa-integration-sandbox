"""Owned, fail-fast launcher for gated C1.2d closed-loop qualification."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
from typing import Callable, Iterable, Mapping

from .owned_process_session import OwnedProcessSession
from .ros_domain import (
    RosDomainError,
    RosDomainLease,
    allocate_isolated_domain,
    claim_explicit_domain,
)
from .runtime_preflight import (
    RuntimePreflightError,
    validate_ackermann_runtime,
    validate_f1tenth_gym_runtime,
)


F1TENTH_GYM_SHA = "bdaec1420c3b0f103858d289866d0d4e2e597c30"
DT_S = 0.01
MAX_SPEED_MPS = 1.0
MAX_STEERING_RAD = 0.288
SHORT_HORIZON_STEPS = 100


REQUIRED_READY_NODES = frozenset(
    {
        "/c1/nav2_raceline",
        "/c1/mppi_lockstep_host",
        "/c1/nav2_ackermann_adapter",
    }
)
REQUIRED_READY_TOPICS = frozenset(
    {
        "/c1/nav2_path",
        "/c1/nav2_cmd_vel",
        "/c1/drive_request",
    }
)


class QualificationHarnessError(RuntimeError):
    """A C1 qualification prerequisite or critical process failed."""


def _lines(command: list[str], *, env: Mapping[str, str] | None = None) -> set[str]:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=None if env is None else dict(env),
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise QualificationHarnessError(f"probe failed ({' '.join(command)}): {detail}")
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def runtime_graph_snapshot(
    env: Mapping[str, str] | None = None,
) -> tuple[set[str], set[str]]:
    return (
        _lines(
            ["ros2", "node", "list", "--no-daemon", "--spin-time", "3.0"], env=env
        ),
        _lines(
            ["ros2", "topic", "list", "--no-daemon", "--spin-time", "3.0"], env=env
        ),
    )


def domain_has_active_graph(domain_id: int) -> bool:
    env = dict(os.environ)
    env["ROS_DOMAIN_ID"] = str(domain_id)
    env["ROS_LOCALHOST_ONLY"] = "1"
    nodes = _lines(
        ["ros2", "node", "list", "--no-daemon", "--spin-time", "3.0"], env=env
    )
    return bool(nodes)


def wait_for_ready(
    session: OwnedProcessSession,
    *,
    timeout_s: float,
    probe: Callable[[], tuple[set[str], set[str]]] = runtime_graph_snapshot,
    poll_s: float = 0.1,
) -> dict[str, list[str]]:
    """Require two consecutive complete graph snapshots while launch is alive."""

    deadline = time.monotonic() + timeout_s
    consecutive = 0
    last_nodes: set[str] = set()
    last_topics: set[str] = set()
    while time.monotonic() < deadline:
        returncode = session.process.poll()
        if returncode is not None:
            raise QualificationHarnessError(
                f"critical runtime exited before ready with status {returncode}"
            )
        last_nodes, last_topics = probe()
        complete = REQUIRED_READY_NODES <= last_nodes and REQUIRED_READY_TOPICS <= last_topics
        consecutive = consecutive + 1 if complete else 0
        if consecutive >= 2:
            return {
                "nodes": sorted(last_nodes),
                "topics": sorted(last_topics),
            }
        time.sleep(poll_s)
    missing_nodes = sorted(REQUIRED_READY_NODES - last_nodes)
    missing_topics = sorted(REQUIRED_READY_TOPICS - last_topics)
    raise QualificationHarnessError(
        f"runtime did not become ready; missing nodes={missing_nodes}, topics={missing_topics}"
    )


def validate_zero_step_artifacts(output_dir: Path) -> dict[str, object]:
    summary_path = output_dir / "summary.json"
    telemetry_path = output_dir / "controller_telemetry.csv"
    if not summary_path.is_file():
        raise QualificationHarnessError("zero-step summary.json was not produced")
    if not telemetry_path.is_file():
        raise QualificationHarnessError("zero-step controller telemetry was not produced")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    with telemetry_path.open(newline="", encoding="utf-8") as stream:
        telemetry = list(csv.DictReader(stream))

    required = {
        "simulator_step_count": 0,
        "accepted_drive_requests": 1,
        "duplicate_state_stamp_rejections": 0,
        "state_stamp_mismatch_events": 0,
        "qualification_limit_reached": True,
        "fault": "qualification_step_limit_reached",
        "steps_after_terminal": 0,
        "final_applied_command": {"steering_rad": 0.0, "speed_mps": 0.0},
    }
    for key, expected in required.items():
        if summary.get(key) != expected:
            raise QualificationHarnessError(
                f"zero-step evidence mismatch for {key}: {summary.get(key)!r} != {expected!r}"
            )
    if len(telemetry) != 1:
        raise QualificationHarnessError(
            f"expected one controller evaluation, observed {len(telemetry)}"
        )
    row = telemetry[0]
    steering = float(row["delta_applied_rad"])
    speed = float(row["upstream_linear_mps"])
    if not math.isfinite(steering) or not math.isfinite(speed):
        raise QualificationHarnessError("zero-step command is non-finite")
    if abs(steering) > 0.288 or speed < 0.0:
        raise QualificationHarnessError("zero-step command violates Ackermann limits")
    if row["physical_feasibility"].lower() not in {"1", "true"}:
        raise QualificationHarnessError("controller did not report physical feasibility")
    if row["safety_veto_pass"].lower() not in {"1", "true"}:
        raise QualificationHarnessError("independent safety veto rejected the command")
    return {
        "controller_evaluations": len(telemetry),
        "gym_steps": summary["simulator_step_count"],
        "state_stamp_ns": int(row["state_stamp_ns"]),
        "steering_rad": steering,
        "speed_mps": speed,
        "physical_feasibility": True,
        "safety_veto_pass": True,
    }

def validate_one_step_artifacts(output_dir: Path) -> dict[str, object]:
    """Prove exactly one state-command-step transition and no feedback of N+1."""

    summary_path = output_dir / "summary.json"
    telemetry_path = output_dir / "controller_telemetry.csv"
    trajectory_path = output_dir / "trajectory.csv"
    if not summary_path.is_file() or not telemetry_path.is_file() or not trajectory_path.is_file():
        raise QualificationHarnessError("one-step evidence artifacts are incomplete")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    with telemetry_path.open(newline="", encoding="utf-8") as stream:
        telemetry = list(csv.DictReader(stream))
    with trajectory_path.open(newline="", encoding="utf-8") as stream:
        trajectory = list(csv.DictReader(stream))

    required = {
        "simulator_step_count": 1,
        "accepted_drive_requests": 1,
        "duplicate_state_stamp_rejections": 0,
        "state_stamp_mismatch_events": 0,
        "qualification_limit_reached": True,
        "fault": "qualification_step_limit_reached",
        "steps_after_terminal": 0,
        "collision_edges": 0,
        "off_track_events": 0,
        "reverse_command_events": 0,
        "invalid_command_events": 0,
        "final_applied_command": {"steering_rad": 0.0, "speed_mps": 0.0},
    }


    for key, expected in required.items():
        if summary.get(key) != expected:
            raise QualificationHarnessError(
                f"one-step evidence mismatch for {key}: {summary.get(key)!r} != {expected!r}"
            )
    if len(telemetry) != 1:
        raise QualificationHarnessError(
            f"expected one controller evaluation, observed {len(telemetry)}"
        )
    if len(trajectory) != 1:
        raise QualificationHarnessError(
            f"expected one Gym state transition, observed {len(trajectory)}"
        )

    row = telemetry[0]
    transition = summary.get("qualification_transition")
    if not isinstance(transition, dict):
        raise QualificationHarnessError("one-step transition metadata is missing")
    state_n = transition.get("state_n")
    state_n1 = transition.get("state_n1")
    if not isinstance(state_n, dict) or not isinstance(state_n1, dict):
        raise QualificationHarnessError("one-step state metadata is missing")

    numeric_values = [
        float(row["upstream_linear_mps"]),
        float(row["upstream_angular_rps"]),
        float(row["kappa_cmd_1pm"]),
        float(row["delta_applied_rad"]),
        *[float(state_n[key]) for key in ("x_m", "y_m", "yaw_rad", "speed_mps")],
        *[float(state_n1[key]) for key in ("x_m", "y_m", "yaw_rad", "speed_mps")],
        float(state_n["full_body_clearance_m"]),
        float(state_n1["full_body_clearance_m"]),
    ]
    if not all(math.isfinite(value) for value in numeric_values):
        raise QualificationHarnessError("one-step evidence contains a non-finite value")

    state_stamp = int(state_n["stamp_ns"])
    state_n1_stamp = int(state_n1["stamp_ns"])
    if int(row["state_stamp_ns"]) != state_stamp:
        raise QualificationHarnessError("controller did not consume state N stamp")
    if state_n1_stamp - state_stamp != int(round(DT_S * 1_000_000_000)):
        raise QualificationHarnessError("state N+1 stamp does not advance by one simulator dt")
    if int(transition.get("command_index", -1)) != 1:
        raise QualificationHarnessError("Gym did not consume command index 1")

    steering = float(row["delta_applied_rad"])
    speed = float(row["upstream_linear_mps"])
    if abs(steering) > 0.288 or speed < 0.0 or speed > MAX_SPEED_MPS:
        raise QualificationHarnessError("one-step command violates Ackermann limits")
    if row["physical_feasibility"].lower() not in {"1", "true"}:
        raise QualificationHarnessError("one-step command is not physically feasible")
    if row["safety_veto_pass"].lower() not in {"1", "true"}:
        raise QualificationHarnessError("independent safety veto rejected the command")
    if row["downstream_steering_saturated"] not in {"0", "false", "False"}:
        raise QualificationHarnessError("downstream feasibility clamp activated")

    dx = float(state_n1["x_m"]) - float(state_n["x_m"])
    dy = float(state_n1["y_m"]) - float(state_n["y_m"])
    dyaw = float(state_n1["yaw_rad"]) - float(state_n["yaw_rad"])
    dspeed = float(state_n1["speed_mps"]) - float(state_n["speed_mps"])
    if math.hypot(dx, dy) > MAX_SPEED_MPS * DT_S * 1.1 + 1e-9:
        raise QualificationHarnessError("one-step state displacement is not physically bounded")
    if abs(steering) > 1e-12 and dyaw * steering <= 0.0:
        raise QualificationHarnessError("observed yaw direction opposes steering command")
    if bool(state_n1.get("collision")) or bool(state_n1.get("off_track")):
        raise QualificationHarnessError("one-step state is colliding or off track")

    return {
        "controller_evaluations": 1,
        "gym_steps": 1,
        "controller_input_stamp_ns": state_stamp,
        "controller_output_stamp_ns": state_stamp,
        "gym_input_command_index": 1,
        "state_n": state_n,
        "state_n1": state_n1,
        "vx_mps": speed,
        "wz_rps": float(row["upstream_angular_rps"]),
        "kappa_1pm": float(row["kappa_cmd_1pm"]),
        "steering_rad": steering,
        "downstream_feasibility_clamp_activations": 0,
        "safety_veto_pass": True,
        "dx_m": dx,
        "dy_m": dy,
        "dyaw_rad": dyaw,
        "dspeed_mps": dspeed,
        "steering_sign_semantics": "PASS",
    }


def _csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise QualificationHarnessError(f"required evidence artifact is missing: {path.name}")
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _truth(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def validate_short_horizon_artifacts(
    output_dir: Path,
    *,
    shutdown: Mapping[str, object],
    step_limit: int = SHORT_HORIZON_STEPS,
) -> dict[str, object]:
    """Validate a bounded lockstep run and identify the first early fault."""
    summary_path = output_dir / "summary.json"
    if not summary_path.is_file():
        raise QualificationHarnessError("short-horizon summary.json was not produced")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    telemetry = _csv_rows(output_dir / "controller_telemetry.csv")
    commands = _csv_rows(output_dir / "commands.csv")
    trajectory = _csv_rows(output_dir / "trajectory.csv")
    events = _csv_rows(output_dir / "events.csv")

    steps = int(summary.get("simulator_step_count", -1))
    candidates: list[tuple[int, str]] = []
    if int(summary.get("qualification_step_limit", -1)) != step_limit:
        candidates.append((1, "qualification_step_limit_mismatch"))
    if not math.isclose(float(summary.get("dt_s", math.nan)), DT_S, rel_tol=0.0, abs_tol=1e-12):
        candidates.append((1, "simulator_dt_mismatch"))
    try:
        sim_time_s = float(summary["sim_time_s"])
    except (KeyError, TypeError, ValueError):
        sim_time_s = math.nan
    if not math.isfinite(sim_time_s) or sim_time_s < 0.0 or sim_time_s > step_limit * DT_S + 1e-9:
        candidates.append((max(min(steps, step_limit) + 1, 1), "simulated_time_limit_exceeded"))
    for row in trajectory:
        step = int(row["step"])
        if _truth(row.get("collision")):
            candidates.append((step, "collision"))
        if _truth(row.get("off_track")):
            candidates.append((step, "off_track"))
    for row in events:
        event = row.get("event", "")
        if event in {"collision_edge", "off_track_edge"}:
            candidates.append((int(row["step"]), "collision" if event == "collision_edge" else "off_track"))

    fault = str(summary.get("fault") or "")
    fault_map = {
        "non_finite_command": "invalid_command",
        "reverse_command": "invalid_command",
        "command_outside_c1_limits": "invalid_command",
        "physical_feasibility_violation": "invalid_command",
        "collision": "collision",
        "off_track": "off_track",
        "independent_full_footprint_safety_veto": "safety_veto",
        "state_stamp_mismatch": "mismatched_state_stamp",
        "non_monotonic_state_stamp": "mismatched_state_stamp",
        "invalid_zero_state_stamp": "invalid_state_stamp",
    }
    if fault and fault != "qualification_step_limit_reached":
        candidates.append((steps + 1 if fault in fault_map and fault_map[fault] in {"invalid_command", "safety_veto"} else max(steps, 1), fault_map.get(fault, fault)))

    violations: list[tuple[int, str]] = []
    for index, row in enumerate(telemetry, start=1):
        try:
            speed = float(row["upstream_linear_mps"])
            steering = float(row["delta_applied_rad"])
        except (KeyError, TypeError, ValueError):
            violations.append((index, "invalid_command"))
            continue
        if not math.isfinite(speed) or not math.isfinite(steering) or not (0.0 <= speed <= MAX_SPEED_MPS) or abs(steering) > MAX_STEERING_RAD:
            violations.append((index, "invalid_command"))
        if row.get("safety_veto_pass", "").strip().lower() not in {"1", "true"}:
            violations.append((index, "safety_veto"))
        if row.get("physical_feasibility", "").strip().lower() not in {"1", "true"}:
            violations.append((index, "invalid_command"))

    for index, row in enumerate(commands, start=1):
        for name in ("requested_speed_mps", "applied_speed_mps", "requested_steering_rad", "applied_steering_rad"):
            try:
                value = float(row[name])
            except (KeyError, TypeError, ValueError):
                violations.append((index, "invalid_command"))
                continue
            if not math.isfinite(value):
                violations.append((index, "invalid_command"))
            elif "speed" in name and not 0.0 <= value <= MAX_SPEED_MPS:
                violations.append((index, "invalid_command"))
            elif "steering" in name and abs(value) > MAX_STEERING_RAD:
                violations.append((index, "invalid_command"))

    candidates.extend(violations)
    if int(summary.get("collision_edges", 0)) > 0 and not any(kind == "collision" for _, kind in candidates):
        candidates.append((max(steps, 1), "collision"))
    if int(summary.get("off_track_events", 0)) > 0 and not any(kind == "off_track" for _, kind in candidates):
        candidates.append((max(steps, 1), "off_track"))
    if int(summary.get("invalid_command_events", 0)) > 0 and not any(kind == "invalid_command" for _, kind in candidates):
        candidates.append((steps + 1, "invalid_command"))
    if int(summary.get("duplicate_state_stamp_rejections", 0)) > 0:
        candidates.append((max(steps + 1, 1), "duplicate_state_stamp"))
    if int(summary.get("state_stamp_mismatch_events", 0)) > 0:
        candidates.append((max(steps + 1, 1), "mismatched_state_stamp"))

    telemetry_stamps = [int(row["state_stamp_ns"]) for row in telemetry if row.get("state_stamp_ns", "").strip()]
    if len(telemetry_stamps) != len(telemetry) or any(stamp <= 0 for stamp in telemetry_stamps):
        candidates.append((max(steps + 1, 1), "invalid_state_stamp"))
    if len(set(telemetry_stamps)) != len(telemetry_stamps):
        candidates.append((max(steps + 1, 1), "duplicate_state_stamp"))
    for index, (left, right) in enumerate(zip(telemetry_stamps, telemetry_stamps[1:]), start=2):
        if right <= left:
            candidates.append((index, "duplicate_state_stamp" if right == left else "mismatched_state_stamp"))
    telemetry_sequences = [int(row["sequence"]) for row in telemetry if row.get("sequence", "").strip()]
    if len(telemetry_sequences) != len(telemetry) or telemetry_sequences != list(range(1, len(telemetry) + 1)):
        candidates.append((max(min(len(telemetry_sequences), steps) + 1, 1), "command_step_order"))

    expected_steps = list(range(1, steps + 1))
    command_steps = [int(row["step"]) for row in commands]
    trajectory_steps = [int(row["step"]) for row in trajectory]
    if command_steps != expected_steps or trajectory_steps != expected_steps:
        candidates.append((max(min(len(commands), len(trajectory)) + 1, 1), "command_step_order"))
    if len(telemetry) < steps or len(telemetry) > steps + 1:
        candidates.append((max(min(len(telemetry), steps) + 1, 1), "command_step_order"))
    accepted = int(summary.get("accepted_drive_requests", -1))
    if accepted != len(commands) and not (accepted == len(commands) + 1 and fault in fault_map):
        candidates.append((max(min(accepted, len(commands)) + 1, 1), "command_step_order"))
    for command, state in zip(commands, trajectory):
        if not math.isclose(float(command["sim_time_s"]), float(state["sim_time_s"]), rel_tol=0.0, abs_tol=1e-9):
            candidates.append((int(command["step"]), "command_step_mismatch"))

    if int(summary.get("steps_after_terminal", -1)) != 0:
        candidates.append((steps + 1, "steps_after_terminal"))
    if summary.get("final_applied_command") != {"steering_rad": 0.0, "speed_mps": 0.0}:
        candidates.append((max(steps, 1), "final_applied_command_not_zero"))
    if not _truth(summary.get("terminal_zero_observed")):
        candidates.append((max(steps, 1), "terminal_zero_not_observed"))
    if not _truth(summary.get("state_stamp_causality_required")):
        candidates.append((1, "state_stamp_causality_not_required"))
    if not _truth(shutdown.get("success")) or list(shutdown.get("remaining_pids", [])):
        candidates.append((max(steps, 1), "owned_processes_remain"))

    first_fault = None
    if candidates:
        first_step, first_reason = min(candidates, key=lambda item: (item[0], item[1]))
        first_fault = {"reason": first_reason, "step": first_step}

    clean_limit = (
        steps == step_limit
        and len(commands) == step_limit
        and len(trajectory) == step_limit
        and len(telemetry) == step_limit
        and summary.get("qualification_limit_reached") is True
        and fault == "qualification_step_limit_reached"
        and int(summary.get("accepted_drive_requests", -1)) == step_limit
        and int(summary.get("duplicate_state_stamp_rejections", -1)) == 0
        and int(summary.get("state_stamp_mismatch_events", -1)) == 0
        and int(summary.get("collision_edges", -1)) == 0
        and int(summary.get("off_track_events", -1)) == 0
        and int(summary.get("invalid_command_events", -1)) == 0
        and int(summary.get("steps_after_terminal", -1)) == 0
        and not candidates
    )
    if not clean_limit and not candidates:
        if steps < step_limit:
            candidates.append((steps + 1, fault or "unexpected_early_termination"))
        elif steps > step_limit:
            candidates.append((step_limit + 1, "step_limit_exceeded"))
        else:
            candidates.append((step_limit, fault or "qualification_limit_not_reached"))
        first_step, first_reason = min(candidates, key=lambda item: (item[0], item[1]))
        first_fault = {"reason": first_reason, "step": first_step}
    return {
        "outcome": "CLEAN_LIMIT_REACHED" if clean_limit else "EARLY_FAULT_OR_INVALID_EVIDENCE",
        "step_limit": step_limit,
        "simulator_steps": steps,
        "dt_s": DT_S,
        "maximum_simulated_time_s": step_limit * DT_S,
        "controller_evaluations": len(telemetry),
        "command_rows": len(commands),
        "trajectory_rows": len(trajectory),
        "summary_fault": fault or None,
        "first_fault": first_fault,
        "owned_processes_remaining": list(shutdown.get("remaining_pids", [])),
        "shutdown_success": bool(shutdown.get("success")),
    }
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("preflight", "readiness", "zero-step", "one-step", "short-horizon"),
        required=True,
    )
    parser.add_argument("--workspace", default="/tmp/laksa-c1.2-runtime")
    parser.add_argument(
        "--ackermann-prefix",
        default="/tmp/laksa-c1-native/ackermann_root/opt/ros/humble",
    )
    parser.add_argument(
        "--f1tenth-gym-checkout",
        default="/tmp/laksa-c1-native/f1tenth_gym",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--domain-id")
    parser.add_argument("--domain-seed", type=int)
    parser.add_argument("--domain-lock-root", default="/tmp/laksa-c1-domain-locks")
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser


def _launch_command(args: argparse.Namespace) -> list[str]:
    include_gym = "false" if args.mode == "readiness" else "true"
    gym_start_delay_s = "0.0" if args.mode == "readiness" else "30.0"
    qualification_step_limit = (
        str(SHORT_HORIZON_STEPS) if args.mode == "short-horizon"
        else "1" if args.mode == "one-step" else "0"
    )
    return [
        "ros2",
        "launch",
        "laksa_speed_race",
        "c1_nav2_mppi_three_lap.launch.py",
        f"output_dir:={args.output_dir}",
        f"qualification_step_limit:={qualification_step_limit}",
        f"include_gym:={include_gym}",
        f"gym_start_delay_s:={gym_start_delay_s}",
    ]


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.mode == "short-horizon" and (not math.isfinite(args.timeout) or args.timeout <= 0.0):
        raise SystemExit("short-horizon --timeout must be a finite positive number")
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    evidence_path = output / "harness_result.json"
    if (output / "summary.json").exists() or (output / "controller_telemetry.csv").exists():
        raise SystemExit("refusing to reuse an output directory containing runtime evidence")

    evidence: dict[str, object] = {
        "mode": args.mode,
        "tested_commit": os.environ.get("LAKSA_GIT_SHA", "UNKNOWN"),
        "domain_id": None,
        "ready_state_criteria": {
            "nodes": sorted(REQUIRED_READY_NODES),
            "topics": sorted(REQUIRED_READY_TOPICS),
            "consecutive_snapshots": 2,
        },
        "status": "FAIL",
    }
    session: OwnedProcessSession | None = None
    domain_lease: RosDomainLease | None = None
    try:
        lock_root = Path(args.domain_lock_root)
        if args.domain_id is not None:
            domain_lease = claim_explicit_domain(
                args.domain_id,
                source="--domain-id",
                occupied=domain_has_active_graph,
                lock_root=lock_root,
            )
        else:
            seed = args.domain_seed
            if seed is None:
                digest = hashlib.sha256(str(output.resolve()).encode("utf-8")).digest()
                seed = int.from_bytes(digest[:8], "big", signed=False)
            domain_lease = allocate_isolated_domain(
                seed,
                occupied=domain_has_active_graph,
                lock_root=lock_root,
            )
        args.domain_id = domain_lease.domain_id
        evidence["domain_id"] = domain_lease.domain_id
        evidence["domain_source"] = domain_lease.source
        evidence["domain_lock_path"] = str(domain_lease.lock_path)
        preflight = validate_ackermann_runtime(args.ackermann_prefix)
        evidence["ackermann_preflight"] = preflight.to_dict()
        gym_preflight = validate_f1tenth_gym_runtime(
            args.f1tenth_gym_checkout,
            F1TENTH_GYM_SHA,
        )
        evidence["f1tenth_gym_preflight"] = gym_preflight.to_dict()
        if args.mode == "preflight":
            evidence["status"] = "PASS"
            return 0
        env = dict(os.environ)
        env["ROS_DOMAIN_ID"] = str(args.domain_id)
        env["ROS_LOCALHOST_ONLY"] = "1"
        with (output / "launch.log").open("wb") as launch_log:
            session = OwnedProcessSession(
                _launch_command(args), env=env, stdout=launch_log, stderr=subprocess.STDOUT
            )
            if args.mode == "readiness":
                evidence["ready_graph"] = wait_for_ready(
                    session,
                    timeout_s=min(args.timeout, 30.0),
                    probe=lambda: runtime_graph_snapshot(env),
                )
                evidence["critical_children_ready"] = True
            else:
                evidence["ready_graph"] = wait_for_ready(
                    session,
                    timeout_s=min(args.timeout, 25.0),
                    probe=lambda: runtime_graph_snapshot(env),
                )
                evidence["critical_children_ready"] = True
                returncode = session.wait_for_leader(timeout=args.timeout)
                if returncode is None:
                    raise QualificationHarnessError(
                        f"{args.mode} launch did not terminate in time"
                    )
                evidence["launch_returncode"] = returncode
                if returncode != 0:
                    raise QualificationHarnessError(
                        f"{args.mode} launch exited with status {returncode}"
                    )
                if args.mode == "zero-step":
                    evidence["zero_step"] = validate_zero_step_artifacts(output)
                elif args.mode == "one-step":
                    evidence["one_step"] = validate_one_step_artifacts(output)

            shutdown = session.shutdown()
            evidence["shutdown"] = {
                "success": shutdown.success,
                "phase": shutdown.phase,
                "pgid": shutdown.pgid,
                "observed_pids": shutdown.observed_pids,
                "remaining_pids": shutdown.remaining_pids,
                "leader_returncode": shutdown.leader_returncode,
            }
            if not shutdown.success:
                raise QualificationHarnessError("owned runtime process group did not terminate")
            if args.mode == "short-horizon":
                result = validate_short_horizon_artifacts(
                    output,
                    shutdown=evidence["shutdown"],
                )
                evidence["short_horizon"] = result
                if result["outcome"] != "CLEAN_LIMIT_REACHED":
                    first_fault = result.get("first_fault") or {}
                    evidence["error"] = (
                        "short-horizon ended before a clean 100-step limit: "
                        f"{first_fault.get('reason', result.get('summary_fault', 'invalid evidence'))} "
                        f"at step {first_fault.get('step', 'unknown')}"
                    )
                    return 1
        evidence["status"] = "PASS"
        return 0
    except (QualificationHarnessError, RosDomainError, RuntimePreflightError) as error:
        evidence["error"] = str(error)
        if session is not None:
            shutdown = session.shutdown()
            evidence["failure_shutdown"] = {
                "success": shutdown.success,
                "phase": shutdown.phase,
                "remaining_pids": shutdown.remaining_pids,
                "leader_returncode": shutdown.leader_returncode,
            }
        if args.mode == "short-horizon":
            summary_path = output / "summary.json"
            observed_steps = None
            observed_fault = None
            if summary_path.is_file():
                try:
                    summary = json.loads(summary_path.read_text(encoding="utf-8"))
                    observed_steps = int(summary.get("simulator_step_count", 0))
                    observed_fault = summary.get("fault")
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass
            message = str(error)
            if "did not terminate in time" in message:
                reason = "timeout"
                step = observed_steps
            elif "exited with status" in message:
                reason = "crashed_child"
                step = observed_steps if observed_steps else None
            elif observed_fault:
                reason = str(observed_fault)
                step = observed_steps if observed_steps else None
            else:
                reason = str(observed_fault or "qualification_failed")
                step = observed_steps if observed_steps else None
            evidence["short_horizon"] = {
                "outcome": "TIMEOUT" if reason == "timeout" else "CRASHED_CHILD_OR_EARLY_FAULT",
                "step_limit": SHORT_HORIZON_STEPS,
                "simulator_steps": observed_steps,
                "dt_s": DT_S,
                "maximum_simulated_time_s": SHORT_HORIZON_STEPS * DT_S,
                "first_fault": {"reason": reason, "step": step},
                "owned_processes_remaining": evidence.get("failure_shutdown", {}).get("remaining_pids", []),
                "shutdown_success": evidence.get("failure_shutdown", {}).get("success", False),
            }
        return 1
    finally:
        if domain_lease is not None:
            domain_lease.release()
        evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())

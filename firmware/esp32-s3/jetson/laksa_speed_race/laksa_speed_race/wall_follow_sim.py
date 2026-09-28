"""Headless pinned-F1TENTH-Gym wall-follow campaign and fault evidence."""

from __future__ import annotations

import argparse
import csv
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .wall_follow_core import (
    ControllerConfig,
    FreshnessConfig,
    MotionRequest,
    RequestFreshnessGate,
    ScanFrame,
    WallFollowController,
)
from .wall_follow_maps import (
    CornerMap,
    CorridorMap,
    campaign_profiles,
    corner_profiles,
    generate_corridor_map,
)


DT_S = 0.01
GYM_STEP_RATE_HZ = 100
SCAN_REQUEST_RATE_HZ = 20
SCAN_INTERVAL_STEPS = GYM_STEP_RATE_HZ // SCAN_REQUEST_RATE_HZ
F1TENTH_GYM_SHA = "bdaec1420c3b0f103858d289866d0d4e2e597c30"
F1TENTH_GYM_ROS_SHA = "08395766c4d9dc5a763381f1dd6fa4a3d68df66e"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_wall_environment(map_stub: Path, seed: int, start_pose: tuple[float, float, float]):
    """Create the unchanged pinned Gym KS/RK4 model with LAKSA_PROXY_V0."""

    import numpy as np
    from f1tenth_gym.envs import F110Env
    from f1tenth_gym.envs.action import LongitudinalActionType, SteerActionType
    from f1tenth_gym.envs.dynamic_models import DynamicModel, VehicleParameters
    from f1tenth_gym.envs.env_config import ControlConfig, EnvConfig, LoopCounterMode, ObservationConfig, SimulationConfig
    from f1tenth_gym.envs.integrators import IntegratorType
    from f1tenth_gym.envs.lidar import LiDARConfig
    from f1tenth_gym.envs.observation import ObservationType

    params = VehicleParameters(
        mu=1.0489,
        C_Sf=4.718,
        C_Sr=5.4562,
        lf=0.162,
        lr=0.162,
        h=0.074,
        m=3.75,
        I=0.04712,
        s_min=-0.288,
        s_max=0.288,
        sv_min=-3.2,
        sv_max=3.2,
        v_switch=7.319,
        a_max=9.51,
        v_min=-5.0,
        v_max=20.0,
        width=0.296,
        length=0.568,
        collision_body_center_x=0.135,
        collision_body_center_y=0.0,
    )
    config = EnvConfig(
        seed=seed,
        map_name=map_stub.with_suffix(".yaml"),
        params=params,
        num_agents=1,
        control_config=ControlConfig(
            longitudinal_mode=LongitudinalActionType.SPEED,
            steering_mode=SteerActionType.STEERING_ANGLE,
        ),
        simulation_config=SimulationConfig(
            timestep=DT_S,
            integrator_timestep=DT_S,
            integrator=IntegratorType.RK4,
            dynamics_model=DynamicModel.KS,
            loop_counter=LoopCounterMode.TOGGLE,
            compute_frenet_frame=False,
            max_laps=None,
        ),
        observation_config=ObservationConfig(type=ObservationType.DIRECT),
        lidar_config=LiDARConfig(
            enabled=True,
            num_beams=1080,
            field_of_view=math.radians(270.0),
            angle_min=math.radians(-135.0),
            angle_max=math.radians(135.0),
            range_min=0.0,
            range_max=30.0,
            noise_std=0.002,
            base_link_to_lidar_tf=(0.31542, 0.0, 0.0),
        ),
        render_enabled=False,
    )
    env = F110Env(config=config)
    observation, _ = env.reset(
        seed=seed,
        options={"poses": np.asarray([start_pose], dtype=np.float32)},
    )
    return env, observation


def _state(observation: dict[str, Any]) -> tuple[float, float, float, float, bool, list[float]]:
    agent = observation["agent_0"]
    state = agent["std_state"]
    return (
        float(state[0]),
        float(state[1]),
        float(state[4]),
        float(state[3]),
        bool(agent["collision"]),
        [float(value) for value in agent["scan"]],
    )


def _minimum_body_clearance(
    profile: CorridorMap | CornerMap,
    x_m: float,
    y_m: float,
    yaw_rad: float,
) -> float:
    cosine, sine = math.cos(yaw_rad), math.sin(yaw_rad)
    center_x = x_m + 0.135 * cosine
    center_y = y_m + 0.135 * sine
    clearances: list[float] = []
    for longitudinal in (-0.284, 0.284):
        for lateral in (-0.148, 0.148):
            corner_x = center_x + longitudinal * cosine - lateral * sine
            corner_y = center_y + longitudinal * sine + lateral * cosine
            clearances.append(profile.point_clearance(corner_x, corner_y))
    return min(clearances)


def _start_pose(
    profile: CorridorMap | CornerMap,
    config: ControllerConfig,
    lateral_offset_m: float,
    yaw_offset_rad: float,
) -> tuple[float, float, float]:
    if isinstance(profile, CornerMap):
        right_wall_y = profile.entry_y_m - profile.width_m / 2.0
    else:
        right_wall_y = profile.bottom_y_m
    return (
        1.0,
        right_wall_y + config.target_wall_distance_m + lateral_offset_m,
        yaw_offset_rad,
    )


def _completion(profile: CorridorMap | CornerMap, x_m: float, y_m: float) -> bool:
    if isinstance(profile, CornerMap):
        return y_m >= 5.70
    return x_m >= 7.20


def _zero_row(
    rows: list[dict[str, Any]],
    field: str,
    threshold: float,
    after_s: float | None,
    window_s: float = 2.0,
) -> dict[str, Any] | None:
    for row in rows:
        if after_s is not None and row["sim_time_s"] + 1e-12 < after_s:
            continue
        if after_s is not None and row["sim_time_s"] - after_s > window_s:
            break
        if row[field] <= threshold:
            return row
    return None


def run_case(
    profile: CorridorMap | CornerMap,
    map_stub: Path,
    *,
    seed: int,
    pose_id: str,
    lateral_offset_m: float,
    yaw_offset_rad: float,
    fault: str | None = None,
    max_steps: int = 3600,
    controller_config: ControllerConfig | None = None,
    freshness_config: FreshnessConfig | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config = controller_config or ControllerConfig()
    start_pose = _start_pose(profile, config, lateral_offset_m, yaw_offset_rad)
    env, observation = create_wall_environment(map_stub, seed, start_pose)
    controller = WallFollowController(config)
    gate = RequestFreshnessGate(freshness_config)
    rows: list[dict[str, Any]] = []
    previous_x, previous_y, *_ = _state(observation)
    distance_travelled = 0.0
    minimum_clearance = math.inf
    collision_count = 0
    completion = False
    failure_reason: str | None = None
    fault_start_s: float | None = None
    fault_start_distance: float | None = None
    request_stop_distance: float | None = None
    first_stop_reason: str | None = None
    positive_request_seen = False
    last_request = MotionRequest(0.0, 0.0, True, "initial", 0.0, 0.0)
    scan_event_count = 0
    controller_update_count = 0
    request_publish_count = 0

    try:
        for step in range(max_steps):
            now_s = step * DT_S
            x_m, y_m, yaw_rad, actual_speed_mps, collision, scan_ranges = _state(observation)
            minimum_clearance = min(minimum_clearance, _minimum_body_clearance(profile, x_m, y_m, yaw_rad))
            if collision:
                collision_count += 1
                failure_reason = "gym_collision"
                break
            if (
                _completion(profile, x_m, y_m)
                and not completion
                and fault not in {"controller_crash", "silent_publisher", "command_burst"}
            ):
                completion = True
                if fault_start_s is None:
                    fault_start_s = now_s
                    fault_start_distance = distance_travelled

            inject = step >= 250
            dropout_active = fault == "restart" and 250 <= step < 310
            compute_request = not completion and not (fault == "controller_crash" and inject) and not dropout_active
            publish_request = not completion and not (fault in {"silent_publisher", "command_burst"} and inject) and not dropout_active
            if fault == "sensor_dropout" and inject:
                compute_request = False
                publish_request = False
            if inject and fault_start_s is None and fault not in {
                None, "obstacle_ahead", "opening_obstacle",
            }:
                fault_start_s = now_s
                fault_start_distance = distance_travelled

            scan_event = step % SCAN_INTERVAL_STEPS == 0
            request_published = False
            if scan_event:
                scan_event_count += 1
            if scan_event and completion:
                last_request = MotionRequest(0.0, 0.0, True, "mission_complete", now_s, now_s)
                gate.receive(last_request, now_s)
                request_publish_count += 1
                request_published = True
            elif scan_event and compute_request:
                header_stamp = now_s
                ranges = scan_ranges
                if fault == "stale_scan" and inject:
                    header_stamp = 2.49
                if fault == "delayed_scan" and inject:
                    header_stamp = now_s - 0.25
                if fault == "malformed_scan" and inject:
                    ranges = [math.nan] * len(scan_ranges)
                scan = ScanFrame(
                    ranges,
                    math.radians(-135.0),
                    math.radians(270.0) / 1079.0,
                    0.0,
                    30.0,
                    header_stamp,
                    now_s,
                )
                last_request, diagnostics = controller.update(scan, now_s)
                controller_update_count += 1
                if last_request.speed_mps > 1e-6:
                    positive_request_seen = True
                if positive_request_seen and last_request.speed_mps <= 1e-6 and first_stop_reason is None:
                    first_stop_reason = last_request.reason
                    request_stop_distance = distance_travelled
                    if fault in {"obstacle_ahead", "opening_obstacle"}:
                        fault_start_s = now_s
                        fault_start_distance = distance_travelled
                if publish_request:
                    gate.receive(last_request, now_s)
                    request_publish_count += 1
                    request_published = True
                if fault == "command_burst" and step == 250:
                    for _ in range(5):
                        gate.receive(last_request, now_s)
            applied = gate.apply(now_s, DT_S)

            import numpy as np

            observation, _, done, truncated, info = env.step(
                np.asarray([[applied.steering_angle_rad, applied.speed_mps]], dtype=np.float32)
            )
            new_x, new_y, new_yaw, new_speed, new_collision, _ = _state(observation)
            segment = math.hypot(new_x - previous_x, new_y - previous_y)
            distance_travelled += segment
            previous_x, previous_y = new_x, new_y
            rows.append(
                {
                    "step": step + 1,
                    "sim_time_s": float(info["sim_time"]),
                    "x_m": new_x,
                    "y_m": new_y,
                    "yaw_rad": new_yaw,
                    "actual_speed_mps": new_speed,
                    "requested_speed_mps": last_request.speed_mps,
                    "requested_steering_rad": last_request.steering_angle_rad,
                    "request_reason": last_request.reason,
                    "applied_speed_mps": applied.speed_mps,
                    "applied_steering_rad": applied.steering_angle_rad,
                    "applied_reason": applied.reason,
                    "distance_travelled_m": distance_travelled,
                    "collision": int(new_collision),
                    "scan_event": int(scan_event),
                    "request_published": int(request_published),
                }
            )
            if new_collision:
                collision_count += 1
                failure_reason = "gym_collision"
                break
            if done or truncated:
                failure_reason = "gym_terminal_before_completion"
                break
            stopping_fault = fault in {
                "controller_crash", "silent_publisher", "stale_scan",
                "delayed_scan", "malformed_scan", "sensor_dropout",
                "command_burst", "obstacle_ahead", "opening_obstacle",
            }
            if (
                (completion or (stopping_fault and fault_start_s is not None and positive_request_seen))
                and applied.speed_mps <= 1e-3
                and new_speed <= 0.02
            ):
                break
        else:
            failure_reason = "step_limit"
    finally:
        env.close()

    request_zero_row = _zero_row(rows, "requested_speed_mps", 1e-6, fault_start_s)
    applied_zero_row = _zero_row(rows, "applied_speed_mps", 1e-3, fault_start_s)
    request_zero_s = None if request_zero_row is None else float(request_zero_row["sim_time_s"])
    applied_zero_s = None if applied_zero_row is None else float(applied_zero_row["sim_time_s"])
    stop_distance = None
    if fault_start_distance is not None and applied_zero_row is not None:
        stop_distance = float(applied_zero_row["distance_travelled_m"]) - fault_start_distance
    if completion and collision_count == 0 and failure_reason is None:
        verdict = "PASS"
    elif fault == "restart" and collision_count == 0 and completion and applied_zero_s is not None:
        verdict = "PASS"
    elif fault is not None and collision_count == 0 and positive_request_seen and applied_zero_s is not None:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    duration_s = len(rows) * DT_S
    scenario_class = "corner_completion" if isinstance(profile, CornerMap) else "corridor_traversal"
    if fault in {"obstacle_ahead", "opening_obstacle"}:
        scenario_class = "safe_stop"
    elif fault is not None:
        scenario_class = "fault_stop_or_recovery"
    summary = {
        "map": profile.name,
        "seed": seed,
        "pose_id": pose_id,
        "start_pose": list(start_pose),
        "fault": fault,
        "verdict": verdict,
        "completion": completion,
        "completion_kind": (
            "corner_completion" if completion and isinstance(profile, CornerMap)
            else "corridor_traversal" if completion
            else None
        ),
        "scenario_class": scenario_class,
        "lap_count": 0,
        "failure_reason": failure_reason,
        "first_stop_reason": first_stop_reason,
        "collision_count": collision_count,
        "progress_m": max((row["x_m"] - start_pose[0] for row in rows), default=0.0),
        "distance_travelled_m": distance_travelled,
        "minimum_full_body_clearance_m": minimum_clearance,
        "requested_speed_min_mps": min((row["requested_speed_mps"] for row in rows), default=0.0),
        "requested_speed_max_mps": max((row["requested_speed_mps"] for row in rows), default=0.0),
        "applied_speed_min_mps": min((row["applied_speed_mps"] for row in rows), default=0.0),
        "applied_speed_max_mps": max((row["applied_speed_mps"] for row in rows), default=0.0),
        "requested_steering_min_rad": min((row["requested_steering_rad"] for row in rows), default=0.0),
        "requested_steering_max_rad": max((row["requested_steering_rad"] for row in rows), default=0.0),
        "applied_steering_min_rad": min((row["applied_steering_rad"] for row in rows), default=0.0),
        "applied_steering_max_rad": max((row["applied_steering_rad"] for row in rows), default=0.0),
        "fault_start_s": fault_start_s,
        "time_to_zero_request_s": None if fault_start_s is None or request_zero_s is None else max(0.0, request_zero_s - fault_start_s),
        "time_to_zero_applied_s": None if fault_start_s is None or applied_zero_s is None else max(0.0, applied_zero_s - fault_start_s),
        "simulated_stop_distance_m": stop_distance,
        "steps": len(rows),
        "gym_step_rate_hz": GYM_STEP_RATE_HZ,
        "configured_scan_request_rate_hz": SCAN_REQUEST_RATE_HZ,
        "scan_event_count": scan_event_count,
        "controller_update_count": controller_update_count,
        "request_publish_count": request_publish_count,
        "observed_controller_update_rate_hz": (
            controller_update_count / duration_s if duration_s > 0.0 else 0.0
        ),
        "observed_request_publish_rate_hz": (
            request_publish_count / duration_s if duration_s > 0.0 else 0.0
        ),
    }
    return summary, rows


def run_campaign(output_dir: Path, source_sha: str, config_path: Path) -> dict[str, Any]:
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    controller_config = ControllerConfig(**config_payload["controller"])
    freshness_config = FreshnessConfig(**config_payload["request_watchdog"])
    maps_dir = output_dir / "maps"
    traces_dir = output_dir / "traces"
    maps_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)
    map_records: dict[str, dict[str, Any]] = {}
    summaries: list[dict[str, Any]] = []
    seeds = (101, 102, 103, 104, 105)
    poses = (
        ("near_wall_heading_left", -0.025, 0.05),
        ("nominal", 0.0, 0.0),
        ("far_wall_heading_right", 0.025, -0.05),
    )
    for profile in campaign_profiles():
        record = generate_corridor_map(profile, maps_dir / profile.name)
        map_records[profile.name] = record
        map_stub = Path(str(record["map_stub"]))
        for seed in seeds:
            for pose_id, offset, yaw in poses:
                summary, _ = run_case(
                    profile,
                    map_stub,
                    seed=seed,
                    pose_id=pose_id,
                    lateral_offset_m=offset,
                    yaw_offset_rad=yaw,
                    controller_config=controller_config,
                    freshness_config=freshness_config,
                )
                summaries.append(summary)

    for profile in corner_profiles():
        record = generate_corridor_map(profile, maps_dir / profile.name)
        map_records[profile.name] = record
        map_stub = Path(str(record["map_stub"]))
        for seed in seeds:
            for pose_id, offset, yaw in poses:
                summary, _ = run_case(
                    profile,
                    map_stub,
                    seed=seed,
                    pose_id=pose_id,
                    lateral_offset_m=offset,
                    yaw_offset_rad=yaw,
                    controller_config=controller_config,
                    freshness_config=freshness_config,
                )
                summaries.append(summary)

    base_profile = campaign_profiles()[0]
    base_stub = Path(str(map_records[base_profile.name]["map_stub"]))
    for fault in (
        "controller_crash",
        "silent_publisher",
        "stale_scan",
        "delayed_scan",
        "malformed_scan",
        "sensor_dropout",
        "command_burst",
        "restart",
    ):
        summary, rows = run_case(
            base_profile,
            base_stub,
            seed=777,
            pose_id="nominal",
            lateral_offset_m=0.0,
            yaw_offset_rad=0.0,
            fault=fault,
            controller_config=controller_config,
            freshness_config=freshness_config,
        )
        summaries.append(summary)
        trace_path = traces_dir / f"fault_{fault}.csv"
        if rows:
            with trace_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)

    stop_profiles = (
        replace(
            base_profile,
            name="obstacle_ahead",
            right_recess_start_m=None,
            right_recess_end_m=None,
            right_recess_depth_m=0.0,
            obstacle_x_m=4.0,
        ),
        replace(base_profile, name="opening_obstacle", obstacle_x_m=3.65),
    )
    for obstacle in stop_profiles:
        obstacle_record = generate_corridor_map(obstacle, maps_dir / obstacle.name)
        map_records[obstacle.name] = obstacle_record
        obstacle_summary, obstacle_rows = run_case(
            obstacle,
            Path(str(obstacle_record["map_stub"])),
            seed=888,
            pose_id="nominal",
            lateral_offset_m=0.0,
            yaw_offset_rad=0.0,
            fault=obstacle.name,
            controller_config=controller_config,
            freshness_config=freshness_config,
        )
        summaries.append(obstacle_summary)
        if obstacle_rows:
            with (traces_dir / f"fault_{obstacle.name}.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(obstacle_rows[0]))
                writer.writeheader()
                writer.writerows(obstacle_rows)

    nominal = [item for item in summaries if item["fault"] is None]
    faults = [item for item in summaries if item["fault"] is not None]
    corridors = [item for item in nominal if item["scenario_class"] == "corridor_traversal"]
    corners = [item for item in nominal if item["scenario_class"] == "corner_completion"]
    safe_stops = [item for item in summaries if item["scenario_class"] == "safe_stop"]
    manifest = {
        "schema_version": "laksa-wall-follow-campaign-v1",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "sandbox_source_sha": source_sha,
        "upstream": {
            "f1tenth_gym": F1TENTH_GYM_SHA,
            "f1tenth_gym_ros": F1TENTH_GYM_ROS_SHA,
        },
        "configuration_file": str(config_path),
        "configuration_sha256": _sha256(config_path),
        "configuration": config_payload,
        "maps": map_records,
        "seeds": list(seeds),
        "poses": [list(item) for item in poses],
        "cadence": {
            "gym_step_rate_hz": GYM_STEP_RATE_HZ,
            "scan_rate_hz": SCAN_REQUEST_RATE_HZ,
            "request_rate_hz": SCAN_REQUEST_RATE_HZ,
            "gym_steps_per_scan": SCAN_INTERVAL_STEPS,
        },
        "nominal_run_count": len(nominal),
        "nominal_pass_count": sum(item["verdict"] == "PASS" for item in nominal),
        "fault_run_count": len(faults),
        "fault_pass_count": sum(item["verdict"] == "PASS" for item in faults),
        "outcomes": {
            "corridor_traversal": {
                "run_count": len(corridors),
                "pass_count": sum(item["verdict"] == "PASS" for item in corridors),
            },
            "safe_stop": {
                "run_count": len(safe_stops),
                "pass_count": sum(item["verdict"] == "PASS" for item in safe_stops),
            },
            "corner_completion": {
                "run_count": len(corners),
                "pass_count": sum(item["verdict"] == "PASS" for item in corners),
            },
            "lap_completion": {
                "run_count": 0,
                "pass_count": 0,
                "status": "UNVERIFIED",
                "reason": "No closed-loop race-lap scenario is part of this wall-follow campaign.",
            },
        },
        "overall": "PASS" if all(item["verdict"] == "PASS" for item in summaries) else "PARTIAL",
        "physical_hardware_touched": False,
        "physical_command_topics_used": False,
        "ground_truth_use": "metrics_and_completion_only",
        "runs": summaries,
    }
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (output_dir / "run_summary.csv").open("w", newline="", encoding="utf-8") as stream:
        if summaries:
            writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
            writer.writeheader()
            writer.writerows(summaries)
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "config" / "wall_follow_v1.json",
    )
    args = parser.parse_args(argv)
    manifest = run_campaign(args.output_dir, args.source_sha, args.config)
    print(json.dumps({key: manifest[key] for key in ("overall", "nominal_run_count", "nominal_pass_count", "fault_run_count", "fault_pass_count")}, indent=2))
    raise SystemExit(0 if manifest["overall"] == "PASS" else 2)


if __name__ == "__main__":
    main()

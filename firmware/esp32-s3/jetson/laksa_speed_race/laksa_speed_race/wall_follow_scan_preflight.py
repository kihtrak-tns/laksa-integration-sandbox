"""Repeatable synthetic preflight shaped like the measured A2M12 scans."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from types import SimpleNamespace

from .wall_follow_core import ControllerConfig, WallFollowController
from .wall_follow_scan_adapter import update_from_laserscan


def _scan(stamp_s: float, ranges: list[float]):
    sec = int(stamp_s)
    nanosec = round((stamp_s - sec) * 1_000_000_000)
    return SimpleNamespace(
        header=SimpleNamespace(stamp=SimpleNamespace(sec=sec, nanosec=nanosec), frame_id="laser"),
        angle_min=-math.pi,
        angle_increment=2.0 * math.pi / 1800,
        range_min=0.05,
        range_max=16.0,
        ranges=ranges,
    )


def _synthetic_ranges() -> list[float]:
    values = []
    for index in range(1800):
        angle = -math.pi + index * (2.0 * math.pi / 1800)
        sine = math.sin(angle)
        distance = 0.254 / -sine if sine < -1e-6 else math.inf
        if index % 7 == 0:
            distance = math.inf
        elif not math.isfinite(distance) or distance < 0.05 or distance >= 16.0:
            # Approximate other indoor returns outside the modeled wall plane.
            distance = 5.0
        values.append(distance)
    return values


def run_preflight() -> dict:
    config = ControllerConfig()
    controller = WallFollowController(config)
    ranges = _synthetic_ranges()
    nominal_rate_hz = 12.8
    outputs = []
    for index in range(12):
        stamp = 100.0 + index / nominal_rate_hz
        request, diagnostics = update_from_laserscan(
            controller, _scan(stamp, ranges), stamp, sensor_x_m=0.31542
        )
        outputs.append(
            {
                "stamp_s": stamp,
                "speed_mps": request.speed_mps,
                "steering_angle_rad": request.steering_angle_rad,
                "brake": request.brake,
                "request_reason": request.reason,
                "diagnostic_reason": diagnostics.reason,
            }
        )

    invalid_request, invalid_diagnostics = update_from_laserscan(
        WallFollowController(config), _scan(200.0, [math.inf] * 1800), 200.0, sensor_x_m=0.31542
    )
    stale_request, stale_diagnostics = update_from_laserscan(
        WallFollowController(config), _scan(300.0, ranges), 300.25, sensor_x_m=0.31542
    )
    speeds = [record["speed_mps"] for record in outputs]
    steering = [record["steering_angle_rad"] for record in outputs]
    return {
        "schema": "laksa-wall-follow-laserscan-preflight-v1",
        "classification": "synthetic_adapter_preflight_not_real_bag_replay",
        "real_a6_replay": "UNVERIFIED",
        "input_shape": {
            "topic_type": "sensor_msgs/msg/LaserScan",
            "frame_id": "laser",
            "beams": 1800,
            "angle_min_rad": -math.pi,
            "angle_increment_rad": 2.0 * math.pi / 1800,
            "range_min_m": 0.05,
            "range_max_m": 16.0,
            "nominal_rate_hz": nominal_rate_hz,
            "synthetic_inf_count": sum(math.isinf(value) for value in ranges),
            "sensor_pose": "unmeasured; simulation default x=0.31542 m, y=0, yaw=0",
        },
        "valid_stream": {
            "message_count": len(outputs),
            "observed_interval_rate_hz": nominal_rate_hz,
            "speed_bounds_mps": [min(speeds), max(speeds)],
            "configured_speed_limit_mps": config.speed_mps,
            "steering_bounds_rad": [min(steering), max(steering)],
            "configured_steering_bounds_rad": [-config.steering_right_limit_rad, config.steering_left_limit_rad],
            "moving_request_count": sum(speed > 0.0 for speed in speeds),
            "requests": outputs,
        },
        "invalid_scan": {
            "diagnostic_reason": invalid_diagnostics.reason,
            "request_reason": invalid_request.reason,
            "speed_mps": invalid_request.speed_mps,
            "steering_angle_rad": invalid_request.steering_angle_rad,
            "brake": invalid_request.brake,
        },
        "stale_header": {
            "age_s": 0.25,
            "diagnostic_reason": stale_diagnostics.reason,
            "request_reason": stale_request.reason,
            "speed_mps": stale_request.speed_mps,
            "steering_angle_rad": stale_request.steering_angle_rad,
            "brake": stale_request.brake,
        },
        "limitations": [
            "No A6 /scan payload was available in this execution session.",
            "No measured laser-to-base transform was included in A6; sensor offset is the simulation default.",
            "This preflight tests conversion, cadence, and controller bounds only; it does not validate car behavior.",
        ],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    payload = json.dumps(run_preflight(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()

"""Read-only scan replay for synthetic fixtures and future exported ROS bags.

The committed fixture is an analytic, deterministic stand-in.  Real RPLIDAR
replay remains pending until a bag and its exact driver/TF configuration are
committed by the hardware bring-up owner.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from .wall_follow_core import ControllerConfig, ScanFrame, WallFollowController


def analytic_ranges(frame: dict[str, Any], fixture: dict[str, Any]) -> list[float]:
    scan = fixture["scan"]
    count = int(scan["beams"])
    angle_min = float(scan["angle_min_rad"])
    angle_increment = float(scan["angle_increment_rad"])
    sensor_x = float(scan["sensor_x_m"])
    sensor_y = float(scan["sensor_y_m"])
    sensor_yaw = float(scan["sensor_yaw_rad"])
    maximum = float(scan["range_max_m"])
    slope = float(frame.get("wall_slope", 0.0))
    intercept = float(frame["wall_intercept_m"])
    ranges: list[float] = []
    for index in range(count):
        angle = sensor_yaw + angle_min + index * angle_increment
        dx, dy = math.cos(angle), math.sin(angle)
        denominator = dy - slope * dx
        if abs(denominator) <= 1e-9:
            ranges.append(maximum)
            continue
        ray = (slope * sensor_x + intercept - sensor_y) / denominator
        ranges.append(ray if 0.0 <= ray <= maximum else maximum)
    return ranges


def replay_fixture(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    if fixture.get("format") != "laksa-analytic-scan-bag-v1":
        raise ValueError("unsupported scan fixture format")
    controller = WallFollowController(ControllerConfig(**fixture.get("controller", {})))
    outputs: list[dict[str, Any]] = []
    scan_spec = fixture["scan"]
    for frame in fixture["frames"]:
        stamp = float(frame["stamp_s"])
        ranges = analytic_ranges(frame, fixture)
        request, diagnostics = controller.update(
            ScanFrame(
                ranges,
                float(scan_spec["angle_min_rad"]),
                float(scan_spec["angle_increment_rad"]),
                float(scan_spec["range_min_m"]),
                float(scan_spec["range_max_m"]),
                stamp,
                stamp,
                float(scan_spec["sensor_x_m"]),
                float(scan_spec["sensor_y_m"]),
                float(scan_spec["sensor_yaw_rad"]),
                str(scan_spec["frame_id"]),
            ),
            stamp,
        )
        outputs.append(
            {
                "stamp_s": stamp,
                "speed_mps": request.speed_mps,
                "steering_angle_rad": request.steering_angle_rad,
                "brake": request.brake,
                "reason": request.reason,
                "wall_distance_m": diagnostics.wall_distance_m,
                "wall_heading_rad": diagnostics.wall_heading_rad,
            }
        )
    return {
        "fixture": str(path),
        "frame_count": len(outputs),
        "moving_request_count": sum(item["speed_mps"] > 0.0 for item in outputs),
        "outputs": outputs,
        "real_rplidar_replay": "PENDING",
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = replay_fixture(args.fixture)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()

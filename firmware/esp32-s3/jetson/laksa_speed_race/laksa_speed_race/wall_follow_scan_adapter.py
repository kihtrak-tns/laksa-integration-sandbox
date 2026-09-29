"""Convert real LaserScan-shaped messages to the pure wall-follow core.

This adapter preserves every range value (including ``inf``) and all timing,
angle, range-limit, and frame metadata.  Sensor extrinsics remain explicit
inputs; the defaults are the simulation assumption, not a measured car TF.
"""

from __future__ import annotations

from .wall_follow_core import ControllerDiagnostics, MotionRequest, ScanFrame, WallFollowController


def scan_frame_from_laserscan(
    message,
    receive_time_s: float,
    *,
    sensor_x_m: float = 0.31542,
    sensor_y_m: float = 0.0,
    sensor_yaw_rad: float = 0.0,
) -> ScanFrame:
    stamp = message.header.stamp
    return ScanFrame(
        ranges_m=tuple(message.ranges),
        angle_min_rad=float(message.angle_min),
        angle_increment_rad=float(message.angle_increment),
        range_min_m=float(message.range_min),
        range_max_m=float(message.range_max),
        header_stamp_s=float(stamp.sec) + float(stamp.nanosec) * 1e-9,
        receive_monotonic_s=float(receive_time_s),
        sensor_x_m=float(sensor_x_m),
        sensor_y_m=float(sensor_y_m),
        sensor_yaw_rad=float(sensor_yaw_rad),
        frame_id=str(message.header.frame_id),
    )


def update_from_laserscan(
    controller: WallFollowController,
    message,
    now_s: float,
    *,
    sensor_x_m: float = 0.31542,
    sensor_y_m: float = 0.0,
    sensor_yaw_rad: float = 0.0,
) -> tuple[MotionRequest, ControllerDiagnostics]:
    frame = scan_frame_from_laserscan(
        message,
        now_s,
        sensor_x_m=sensor_x_m,
        sensor_y_m=sensor_y_m,
        sensor_yaw_rad=sensor_yaw_rad,
    )
    return controller.update(frame, now_s)

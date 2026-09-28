"""Portable wall-following controller and simulation-only request watchdog.

This module has no ROS or vehicle dependencies.  Its output is a motion
*request* consumed by a mock/simulation authority.  It must never be wired
directly to ``/laksa/command`` or another physical command topic.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import statistics
from typing import Sequence


@dataclass(frozen=True)
class ScanFrame:
    ranges_m: Sequence[float]
    angle_min_rad: float
    angle_increment_rad: float
    range_min_m: float
    range_max_m: float
    header_stamp_s: float
    receive_monotonic_s: float
    sensor_x_m: float = 0.31542
    sensor_y_m: float = 0.0
    sensor_yaw_rad: float = 0.0
    frame_id: str = "sim_laksa_lidar"


@dataclass(frozen=True)
class MotionRequest:
    speed_mps: float
    steering_angle_rad: float
    brake: bool
    reason: str
    header_stamp_s: float
    receive_monotonic_s: float


@dataclass(frozen=True)
class ControllerDiagnostics:
    state: str
    reason: str
    valid_points: int
    wall_inliers: int
    wall_distance_m: float | None
    wall_heading_rad: float | None
    front_clearance_m: float | None
    front_ttc_s: float | None
    header_age_s: float
    receive_age_s: float


@dataclass(frozen=True)
class ControllerConfig:
    side: int = -1  # -1 follows the right wall; +1 follows the left wall.
    target_wall_distance_m: float = 0.254
    lookahead_m: float = 0.35
    kp_lateral: float = 1.9
    ki_lateral: float = 0.18
    kd_lateral: float = 0.32
    kp_heading: float = 1.15
    derivative_alpha: float = 0.72
    integral_limit: float = 0.25
    speed_mps: float = 0.38
    minimum_speed_mps: float = 0.18
    steering_left_limit_rad: float = 0.288
    steering_right_limit_rad: float = 0.288
    steering_slew_rad_s: float = 1.8
    speed_slew_mps2: float = 0.8
    body_front_m: float = 0.419
    front_corridor_half_width_m: float = 0.17
    front_stop_clearance_m: float = 0.20
    front_slow_clearance_m: float = 0.75
    front_ttc_stop_s: float = 0.65
    front_sector_half_angle_rad: float = math.radians(60.0)
    max_scan_header_age_s: float = 0.18
    max_scan_receive_age_s: float = 0.18
    maximum_invalid_fraction: float = 0.75
    minimum_wall_points: int = 18
    maximum_wall_distance_m: float = 1.25
    fit_x_min_m: float = -0.35
    fit_x_max_m: float = 1.10
    fit_residual_floor_m: float = 0.025
    recovery_valid_frames: int = 4
    opening_distance_jump_m: float = 0.12
    opening_heading_limit_rad: float = 0.35
    maximum_opening_hold_s: float = 7.0

    def __post_init__(self) -> None:
        if self.side not in (-1, 1):
            raise ValueError("side must be -1 (right) or +1 (left)")
        if self.recovery_valid_frames < 1:
            raise ValueError("recovery_valid_frames must be positive")


def _median(values: Sequence[float]) -> float:
    return float(statistics.median(values))


def _slew(current: float, target: float, maximum_rate: float, dt_s: float) -> float:
    step = max(0.0, maximum_rate) * max(0.0, dt_s)
    return current + max(-step, min(step, target - current))


def _bounded(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _robust_line(points: Sequence[tuple[float, float]], residual_floor_m: float) -> tuple[float, float, int]:
    """Return ``y = slope*x + intercept`` using a deterministic robust fit."""

    if len(points) < 2:
        raise ValueError("at least two wall points are required")
    stride = max(1, len(points) // 80)
    sample = list(points[::stride])[:100]
    slopes: list[float] = []
    for offset in (1, 3, 7, 13):
        for index in range(0, len(sample) - offset):
            dx = sample[index + offset][0] - sample[index][0]
            if abs(dx) >= 0.08:
                slopes.append((sample[index + offset][1] - sample[index][1]) / dx)
    slope = _median(slopes) if slopes else 0.0
    intercept = _median([y - slope * x for x, y in sample])
    residuals = [abs(y - (slope * x + intercept)) for x, y in points]
    median_residual = _median(residuals)
    mad = _median([abs(value - median_residual) for value in residuals])
    threshold = max(residual_floor_m, median_residual + 3.0 * max(mad, 0.003))
    inliers = [point for point, residual in zip(points, residuals) if residual <= threshold]
    if len(inliers) < 2:
        raise ValueError("wall fit produced fewer than two inliers")
    mean_x = sum(x for x, _ in inliers) / len(inliers)
    mean_y = sum(y for _, y in inliers) / len(inliers)
    denominator = sum((x - mean_x) ** 2 for x, _ in inliers)
    if denominator <= 1e-12:
        slope = 0.0
    else:
        slope = sum((x - mean_x) * (y - mean_y) for x, y in inliers) / denominator
    intercept = mean_y - slope * mean_x
    return slope, intercept, len(inliers)


class WallFollowController:
    """Robust side-wall estimator and bounded request generator."""

    def __init__(self, config: ControllerConfig | None = None):
        self.config = config or ControllerConfig()
        self._last_time_s: float | None = None
        self._last_error = 0.0
        self._filtered_derivative = 0.0
        self._integral = 0.0
        self._steering = 0.0
        self._speed = 0.0
        self._recovery_count = 0
        self._motion_enabled = False
        self._last_wall_seen_s: float | None = None
        self._opening_start_s: float | None = None

    def _bridge_opening(
        self,
        scan: ScanFrame,
        now_s: float,
        diagnostics: ControllerDiagnostics,
    ) -> tuple[MotionRequest, ControllerDiagnostics] | None:
        """Hold a conservative straight course across a bounded side opening."""

        if self._last_wall_seen_s is None or not self._motion_enabled:
            return None
        if self._opening_start_s is None:
            self._opening_start_s = now_s
        if now_s - self._opening_start_s > self.config.maximum_opening_hold_s:
            return None
        dt_s = 0.0 if self._last_time_s is None else max(0.0, now_s - self._last_time_s)
        self._last_time_s = now_s
        self._integral = 0.0
        self._steering = _slew(self._steering, 0.0, self.config.steering_slew_rad_s, dt_s)
        self._speed = _slew(self._speed, self.config.minimum_speed_mps, self.config.speed_slew_mps2, dt_s)
        request = MotionRequest(self._speed, self._steering, False, "opening_bridge", scan.header_stamp_s, now_s)
        return request, ControllerDiagnostics(
            "OPENING_BRIDGE",
            "opening_bridge",
            diagnostics.valid_points,
            diagnostics.wall_inliers,
            diagnostics.wall_distance_m,
            diagnostics.wall_heading_rad,
            diagnostics.front_clearance_m,
            diagnostics.front_ttc_s,
            diagnostics.header_age_s,
            diagnostics.receive_age_s,
        )

    def _stop(self, scan: ScanFrame, now_s: float, reason: str, diagnostics: ControllerDiagnostics) -> tuple[MotionRequest, ControllerDiagnostics]:
        dt_s = 0.0 if self._last_time_s is None else max(0.0, now_s - self._last_time_s)
        self._last_time_s = now_s
        self._recovery_count = 0
        self._motion_enabled = False
        self._integral = 0.0
        self._speed = _slew(self._speed, 0.0, self.config.speed_slew_mps2 * 2.0, dt_s)
        self._steering = _slew(self._steering, 0.0, self.config.steering_slew_rad_s, dt_s)
        request = MotionRequest(0.0, 0.0, True, reason, scan.header_stamp_s, now_s)
        return request, ControllerDiagnostics(
            state="STOPPED",
            reason=reason,
            valid_points=diagnostics.valid_points,
            wall_inliers=diagnostics.wall_inliers,
            wall_distance_m=diagnostics.wall_distance_m,
            wall_heading_rad=diagnostics.wall_heading_rad,
            front_clearance_m=diagnostics.front_clearance_m,
            front_ttc_s=diagnostics.front_ttc_s,
            header_age_s=diagnostics.header_age_s,
            receive_age_s=diagnostics.receive_age_s,
        )

    def update(self, scan: ScanFrame, now_s: float) -> tuple[MotionRequest, ControllerDiagnostics]:
        cfg = self.config
        header_age = now_s - scan.header_stamp_s
        receive_age = now_s - scan.receive_monotonic_s
        empty = ControllerDiagnostics("STOPPED", "unprocessed", 0, 0, None, None, None, None, header_age, receive_age)
        if (
            not scan.ranges_m
            or not math.isfinite(scan.angle_min_rad)
            or not math.isfinite(scan.angle_increment_rad)
            or scan.angle_increment_rad <= 0.0
            or scan.range_min_m < 0.0
            or scan.range_max_m <= scan.range_min_m
        ):
            return self._stop(scan, now_s, "malformed_scan", empty)
        if header_age < -0.02 or header_age > cfg.max_scan_header_age_s:
            return self._stop(scan, now_s, "stale_scan_header", empty)
        if receive_age < -0.02 or receive_age > cfg.max_scan_receive_age_s:
            return self._stop(scan, now_s, "stale_scan_receive", empty)

        points: list[tuple[float, float, float]] = []
        valid_ranges = 0
        for index, raw_range in enumerate(scan.ranges_m):
            try:
                distance = float(raw_range)
            except (TypeError, ValueError):
                continue
            # A return at the configured maximum is the simulator's no-hit
            # sentinel, not an obstacle point.  Treat it like +inf from a
            # physical LaserScan so it cannot create a false wall or stop.
            if not math.isfinite(distance) or distance < scan.range_min_m or distance >= scan.range_max_m:
                continue
            angle = scan.sensor_yaw_rad + scan.angle_min_rad + index * scan.angle_increment_rad
            cosine, sine = math.cos(angle), math.sin(angle)
            x_m = scan.sensor_x_m + distance * cosine
            y_m = scan.sensor_y_m + distance * sine
            points.append((x_m, y_m, math.atan2(y_m, x_m)))
            valid_ranges += 1
        invalid_fraction = 1.0 - valid_ranges / len(scan.ranges_m)
        if invalid_fraction > cfg.maximum_invalid_fraction:
            bad = ControllerDiagnostics("STOPPED", "too_many_invalid_ranges", valid_ranges, 0, None, None, None, None, header_age, receive_age)
            return self._stop(scan, now_s, "too_many_invalid_ranges", bad)

        # Front safety is independent of wall availability.  Evaluate it
        # before any opening/wall-loss branch can return a moving request.
        front_candidates = [
            x_m - cfg.body_front_m
            for x_m, y_m, bearing in points
            if x_m > cfg.body_front_m
            and abs(bearing) <= cfg.front_sector_half_angle_rad
            and abs(y_m) <= cfg.front_corridor_half_width_m
        ]
        front_clearance = min(front_candidates) if front_candidates else None
        front_ttc = None
        if front_clearance is not None and self._speed > 0.02:
            front_ttc = front_clearance / self._speed
        front_diagnostics = ControllerDiagnostics(
            "TRACKING", "front_checked", valid_ranges, 0, None, None,
            front_clearance, front_ttc, header_age, receive_age,
        )
        if front_clearance is not None and front_clearance <= cfg.front_stop_clearance_m:
            return self._stop(scan, now_s, "front_clearance_stop", front_diagnostics)
        if front_ttc is not None and front_ttc <= cfg.front_ttc_stop_s:
            return self._stop(scan, now_s, "front_ttc_stop", front_diagnostics)

        side_points = [
            (x_m, y_m)
            for x_m, y_m, _ in points
            if cfg.fit_x_min_m <= x_m <= cfg.fit_x_max_m
            and 0.04 <= cfg.side * y_m <= cfg.maximum_wall_distance_m
        ]
        if len(side_points) < cfg.minimum_wall_points:
            lost = ControllerDiagnostics(
                "STOPPED", "wall_lost", valid_ranges, 0, None, None,
                front_clearance, front_ttc, header_age, receive_age,
            )
            bridged = self._bridge_opening(scan, now_s, lost)
            if bridged is not None:
                return bridged
            return self._stop(scan, now_s, "wall_lost", lost)
        try:
            slope, intercept, inlier_count = _robust_line(side_points, cfg.fit_residual_floor_m)
        except ValueError:
            failed = ControllerDiagnostics("STOPPED", "wall_fit_failed", valid_ranges, 0, None, None, None, None, header_age, receive_age)
            return self._stop(scan, now_s, "wall_fit_failed", failed)
        if inlier_count < cfg.minimum_wall_points or cfg.side * intercept <= 0.0:
            failed = ControllerDiagnostics("STOPPED", "wall_fit_rejected", valid_ranges, inlier_count, None, None, None, None, header_age, receive_age)
            return self._stop(scan, now_s, "wall_fit_rejected", failed)

        wall_y_lookahead = slope * cfg.lookahead_m + intercept
        wall_distance = abs(wall_y_lookahead)
        heading = math.atan(slope)
        wall_discontinuous = (
            wall_distance > cfg.target_wall_distance_m + cfg.opening_distance_jump_m
            or abs(heading) > cfg.opening_heading_limit_rad
        )
        if wall_discontinuous:
            discontinuity = ControllerDiagnostics(
                "OPENING_BRIDGE", "wall_discontinuity", valid_ranges, inlier_count,
                wall_distance, heading, front_clearance, front_ttc, header_age, receive_age,
            )
            bridged = self._bridge_opening(scan, now_s, discontinuity)
            if bridged is not None:
                return bridged
        else:
            self._last_wall_seen_s = now_s
            self._opening_start_s = None
        diag = ControllerDiagnostics(
            "TRACKING",
            "tracking",
            valid_ranges,
            inlier_count,
            wall_distance,
            heading,
            front_clearance,
            front_ttc,
            header_age,
            receive_age,
        )
        self._recovery_count += 1
        if not self._motion_enabled and self._recovery_count < cfg.recovery_valid_frames:
            # Keep the control clock advancing during the recovery gate so the
            # first enabled request has a real (and bounded) slew interval.
            self._last_time_s = now_s
            request = MotionRequest(0.0, 0.0, True, "recovery_gate", scan.header_stamp_s, now_s)
            return request, ControllerDiagnostics(
                "RECOVERY", "recovery_gate", valid_ranges, inlier_count, wall_distance,
                heading, front_clearance, front_ttc, header_age, receive_age,
            )
        self._motion_enabled = True

        dt_s = 0.0 if self._last_time_s is None else max(1e-4, now_s - self._last_time_s)
        self._last_time_s = now_s
        lateral_error = -cfg.side * (cfg.target_wall_distance_m - wall_distance)
        derivative = (lateral_error - self._last_error) / dt_s if dt_s > 0.0 else 0.0
        self._filtered_derivative = (
            cfg.derivative_alpha * self._filtered_derivative
            + (1.0 - cfg.derivative_alpha) * derivative
        )
        candidate_integral = _bounded(
            self._integral + lateral_error * dt_s,
            -cfg.integral_limit,
            cfg.integral_limit,
        )
        raw_steering = (
            cfg.kp_lateral * lateral_error
            + cfg.ki_lateral * candidate_integral
            + cfg.kd_lateral * self._filtered_derivative
            + cfg.kp_heading * heading
        )
        limited_steering = _bounded(
            raw_steering,
            -abs(cfg.steering_right_limit_rad),
            abs(cfg.steering_left_limit_rad),
        )
        if math.isclose(raw_steering, limited_steering, abs_tol=1e-12) or raw_steering * lateral_error < 0.0:
            self._integral = candidate_integral
        self._last_error = lateral_error
        self._steering = _slew(self._steering, limited_steering, cfg.steering_slew_rad_s, dt_s)

        steering_fraction = min(1.0, abs(self._steering) / max(cfg.steering_left_limit_rad, cfg.steering_right_limit_rad))
        target_speed = cfg.speed_mps - (cfg.speed_mps - cfg.minimum_speed_mps) * steering_fraction
        if front_clearance is not None and front_clearance < cfg.front_slow_clearance_m:
            span = cfg.front_slow_clearance_m - cfg.front_stop_clearance_m
            scale = _bounded((front_clearance - cfg.front_stop_clearance_m) / max(span, 1e-6), 0.0, 1.0)
            target_speed = min(target_speed, cfg.minimum_speed_mps + scale * (cfg.speed_mps - cfg.minimum_speed_mps))
        self._speed = _slew(self._speed, target_speed, cfg.speed_slew_mps2, dt_s)
        request = MotionRequest(self._speed, self._steering, False, "tracking", scan.header_stamp_s, now_s)
        return request, diag


@dataclass(frozen=True)
class FreshnessConfig:
    request_timeout_s: float = 0.20
    acceleration_limit_mps2: float = 0.8
    stop_deceleration_mps2: float = 1.6
    steering_slew_rad_s: float = 2.2


class RequestFreshnessGate:
    """Independent simulated authority; stale requests ramp to zero, never freeze."""

    def __init__(self, config: FreshnessConfig | None = None):
        self.config = config or FreshnessConfig()
        self._latest: MotionRequest | None = None
        self._received_s: float | None = None
        self._speed = 0.0
        self._steering = 0.0
        self.reason = "no_request"

    def receive(self, request: MotionRequest, now_s: float) -> None:
        if not all(math.isfinite(value) for value in (request.speed_mps, request.steering_angle_rad, now_s)):
            return
        self._latest = request
        self._received_s = now_s

    def apply(self, now_s: float, dt_s: float) -> MotionRequest:
        cfg = self.config
        fresh = (
            self._latest is not None
            and self._received_s is not None
            and 0.0 <= now_s - self._received_s <= cfg.request_timeout_s
        )
        if fresh:
            target = self._latest
            assert target is not None
            target_speed = 0.0 if target.brake else max(0.0, target.speed_mps)
            target_steering = 0.0 if target.brake else target.steering_angle_rad
            rate = cfg.stop_deceleration_mps2 if target.brake else cfg.acceleration_limit_mps2
            self.reason = target.reason
        else:
            target_speed = 0.0
            target_steering = 0.0
            rate = cfg.stop_deceleration_mps2
            self.reason = "request_watchdog_timeout" if self._latest is not None else "no_request"
        self._speed = _slew(self._speed, target_speed, rate, dt_s)
        self._steering = _slew(self._steering, target_steering, cfg.steering_slew_rad_s, dt_s)
        stopped = self._speed <= 1e-6
        if stopped:
            self._speed = 0.0
        return MotionRequest(
            self._speed,
            self._steering,
            not fresh or (self._latest.brake if self._latest is not None else True),
            self.reason,
            self._latest.header_stamp_s if self._latest is not None else now_s,
            now_s,
        )

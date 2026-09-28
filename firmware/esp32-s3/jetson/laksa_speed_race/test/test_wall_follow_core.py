import math
import unittest

from laksa_speed_race.wall_follow_core import (
    ControllerConfig,
    MotionRequest,
    RequestFreshnessGate,
    ScanFrame,
    WallFollowController,
)


def synthetic_scan(*, intercept=-0.254, slope=0.0, obstacle_x=None, invalid=False, stamp=0.0):
    count = 1080
    angle_min = math.radians(-135.0)
    increment = math.radians(270.0) / (count - 1)
    sensor_x = 0.31542
    ranges = []
    for index in range(count):
        angle = angle_min + index * increment
        dx, dy = math.cos(angle), math.sin(angle)
        candidates = []
        denominator = dy - slope * dx
        if abs(denominator) > 1e-9:
            ray = (slope * sensor_x + intercept) / denominator
            if ray > 0.0:
                candidates.append(ray)
        # Opposite wall prevents a mostly-invalid artificial scan.
        if abs(dy) > 1e-9:
            ray = 0.75 / dy
            if ray > 0.0:
                candidates.append(ray)
        if obstacle_x is not None and dx > 1e-9:
            ray = (obstacle_x - sensor_x) / dx
            y = ray * dy
            if ray > 0.0 and -0.40 <= y <= 0.40:
                candidates.append(ray)
        ranges.append(min(candidates, default=30.0))
    if invalid:
        ranges = [math.nan] * len(ranges)
    return ScanFrame(ranges, angle_min, increment, 0.0, 30.0, stamp, stamp)


def recover(controller, scan):
    result = None
    for index in range(controller.config.recovery_valid_frames):
        stamp = index * 0.05
        result = controller.update(
            ScanFrame(
                scan.ranges_m,
                scan.angle_min_rad,
                scan.angle_increment_rad,
                scan.range_min_m,
                scan.range_max_m,
                stamp,
                stamp,
            ),
            stamp,
        )
    return result


class WallFollowerTests(unittest.TestCase):
    def test_right_wall_nominal_recovers_then_moves(self):
        controller = WallFollowController()
        request, diagnostics = recover(controller, synthetic_scan())
        self.assertFalse(request.brake)
        self.assertGreater(request.speed_mps, 0.0)
        self.assertAlmostEqual(diagnostics.wall_distance_m, 0.254, places=2)
        self.assertAlmostEqual(diagnostics.wall_heading_rad, 0.0, places=2)

    def test_right_wall_too_close_steers_left(self):
        controller = WallFollowController()
        request, _ = recover(controller, synthetic_scan(intercept=-0.18))
        self.assertGreater(request.steering_angle_rad, 0.0)

    def test_left_wall_too_close_steers_right(self):
        controller = WallFollowController(ControllerConfig(side=1))
        request, _ = recover(controller, synthetic_scan(intercept=0.18))
        self.assertLess(request.steering_angle_rad, 0.0)

    def test_angled_wall_heading_correction_has_expected_sign(self):
        controller = WallFollowController()
        request, diagnostics = recover(controller, synthetic_scan(intercept=-0.254, slope=-0.12))
        self.assertLess(diagnostics.wall_heading_rad, 0.0)
        self.assertLess(request.steering_angle_rad, 0.0)

    def test_invalid_and_stale_scans_stop(self):
        controller = WallFollowController()
        request, _ = controller.update(synthetic_scan(invalid=True), 0.0)
        self.assertTrue(request.brake)
        self.assertEqual(request.reason, "too_many_invalid_ranges")
        stale = synthetic_scan(stamp=0.0)
        request, _ = controller.update(stale, 0.5)
        self.assertTrue(request.brake)
        self.assertEqual(request.reason, "stale_scan_header")

    def test_front_obstacle_requests_stop(self):
        controller = WallFollowController()
        request, diagnostics = recover(controller, synthetic_scan(obstacle_x=0.55))
        self.assertTrue(request.brake)
        self.assertIn(request.reason, {"front_clearance_stop", "front_ttc_stop"})
        self.assertIsNotNone(diagnostics.front_clearance_m)

    def test_limits_are_finite_and_bounded(self):
        controller = WallFollowController()
        request, _ = recover(controller, synthetic_scan(intercept=-0.06, slope=0.8))
        self.assertTrue(math.isfinite(request.steering_angle_rad))
        self.assertLessEqual(request.steering_angle_rad, controller.config.steering_left_limit_rad)
        self.assertGreaterEqual(request.steering_angle_rad, -controller.config.steering_right_limit_rad)

    def test_watchdog_continues_toward_zero_after_silence(self):
        gate = RequestFreshnessGate()
        request = MotionRequest(0.4, 0.2, False, "tracking", 0.0, 0.0)
        gate.receive(request, 0.0)
        speeds = [gate.apply(index * 0.05, 0.05).speed_mps for index in range(12)]
        self.assertGreater(max(speeds), 0.0)
        self.assertEqual(speeds[-1], 0.0)
        self.assertEqual(gate.reason, "request_watchdog_timeout")


if __name__ == "__main__":
    unittest.main()

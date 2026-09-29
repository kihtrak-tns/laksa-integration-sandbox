import math
from types import SimpleNamespace
import unittest

from laksa_speed_race.wall_follow_bag_export import copy_scan_records, scan_topic_metadata
from laksa_speed_race.wall_follow_core import ControllerConfig, WallFollowController
from laksa_speed_race.wall_follow_scan_preflight import run_preflight
from laksa_speed_race.wall_follow_scan_adapter import scan_frame_from_laserscan, update_from_laserscan


def scan_message(stamp_s, ranges):
    sec = int(stamp_s)
    nanosec = round((stamp_s - sec) * 1_000_000_000)
    return SimpleNamespace(
        header=SimpleNamespace(
            stamp=SimpleNamespace(sec=sec, nanosec=nanosec),
            frame_id="laser",
        ),
        angle_min=-math.pi,
        angle_increment=2.0 * math.pi / 1800,
        range_min=0.05,
        range_max=16.0,
        ranges=ranges,
    )


def corridor_ranges():
    values = []
    for index in range(1800):
        angle = -math.pi + index * (2.0 * math.pi / 1800)
        sine = math.sin(angle)
        distance = 0.254 / -sine if sine < -1e-6 else math.inf
        if index % 7 == 0:
            distance = math.inf
        elif not math.isfinite(distance) or distance < 0.05 or distance >= 16.0:
            distance = 5.0
        values.append(distance)
    return values


class ScanAdapterTests(unittest.TestCase):
    def test_scan_adapter_preserves_ros_fields_and_inf(self):
        message = scan_message(1234.125, [0.5, math.inf, 2.0])
        frame = scan_frame_from_laserscan(message, 1234.13, sensor_x_m=0.0, sensor_yaw_rad=0.0)
        self.assertEqual(frame.header_stamp_s, 1234.125)
        self.assertEqual(frame.frame_id, "laser")
        self.assertEqual(frame.angle_min_rad, message.angle_min)
        self.assertEqual(frame.angle_increment_rad, message.angle_increment)
        self.assertEqual(frame.range_min_m, 0.05)
        self.assertEqual(frame.range_max_m, 16.0)
        self.assertEqual(frame.ranges_m, (0.5, math.inf, 2.0))

    def test_1800_beam_12_8_hz_stream_stays_bounded(self):
        controller = WallFollowController(ControllerConfig())
        outputs = []
        for index in range(12):
            stamp = 100.0 + index / 12.8
            request, diagnostics = update_from_laserscan(
                controller,
                scan_message(stamp, corridor_ranges()),
                stamp,
                sensor_x_m=0.31542,
            )
            outputs.append((request, diagnostics))
        self.assertEqual(len(outputs), 12)
        self.assertTrue(any(request.speed_mps > 0.0 for request, _ in outputs))
        for request, _ in outputs:
            self.assertGreaterEqual(request.speed_mps, 0.0)
            self.assertLessEqual(request.speed_mps, ControllerConfig().speed_mps)
            self.assertGreaterEqual(request.steering_angle_rad, -ControllerConfig().steering_right_limit_rad)
            self.assertLessEqual(request.steering_angle_rad, ControllerConfig().steering_left_limit_rad)
        self.assertGreaterEqual(sum(math.isinf(value) for value in corridor_ranges()), 1)

    def test_invalid_and_stale_scans_request_stop(self):
        controller = WallFollowController()
        invalid, invalid_diag = update_from_laserscan(
            controller, scan_message(10.0, [math.inf] * 1800), 10.0, sensor_x_m=0.0
        )
        self.assertEqual(invalid_diag.reason, "too_many_invalid_ranges")
        self.assertEqual(invalid.speed_mps, 0.0)
        self.assertTrue(invalid.brake)

        stale, stale_diag = update_from_laserscan(
            controller, scan_message(20.0, corridor_ranges()), 20.25, sensor_x_m=0.0
        )
        self.assertEqual(stale_diag.reason, "stale_scan_header")
        self.assertEqual(stale.speed_mps, 0.0)
        self.assertTrue(stale.brake)

    def test_scan_only_export_filters_topics_without_changing_payload_or_stamp(self):
        scan_meta = SimpleNamespace(name="/scan", type="sensor_msgs/msg/LaserScan")
        other_meta = SimpleNamespace(name="/zed/image", type="sensor_msgs/msg/Image")
        self.assertIs(scan_topic_metadata([other_meta, scan_meta]), scan_meta)
        scan_bytes = b"cdr-laserscan-with-inf"
        rows = [
            ("/zed/image", b"large-image-payload", 1),
            ("/scan", scan_bytes, 2_000_000_000),
            ("/scan", b"second-scan", 2_078_125_000),
        ]
        copied = []
        result = copy_scan_records(rows, lambda *row: copied.append(row))
        self.assertEqual(result, (2, 2_000_000_000, 2_078_125_000))
        self.assertEqual(copied, rows[1:])

    def test_preflight_records_a6_shaped_bounds_and_stop_cases(self):
        result = run_preflight()
        self.assertEqual(result["classification"], "synthetic_adapter_preflight_not_real_bag_replay")
        self.assertEqual(result["real_a6_replay"], "UNVERIFIED")
        self.assertEqual(result["input_shape"]["beams"], 1800)
        self.assertEqual(result["input_shape"]["nominal_rate_hz"], 12.8)
        valid = result["valid_stream"]
        self.assertEqual(valid["message_count"], 12)
        self.assertGreater(valid["moving_request_count"], 0)
        self.assertGreaterEqual(valid["speed_bounds_mps"][0], 0.0)
        self.assertLessEqual(valid["speed_bounds_mps"][1], valid["configured_speed_limit_mps"])
        self.assertGreaterEqual(valid["steering_bounds_rad"][0], valid["configured_steering_bounds_rad"][0])
        self.assertLessEqual(valid["steering_bounds_rad"][1], valid["configured_steering_bounds_rad"][1])
        self.assertEqual(result["invalid_scan"]["diagnostic_reason"], "too_many_invalid_ranges")
        self.assertEqual(result["invalid_scan"]["speed_mps"], 0.0)
        self.assertTrue(result["invalid_scan"]["brake"])
        self.assertEqual(result["stale_header"]["diagnostic_reason"], "stale_scan_header")
        self.assertEqual(result["stale_header"]["speed_mps"], 0.0)
        self.assertTrue(result["stale_header"]["brake"])


if __name__ == "__main__":
    unittest.main()

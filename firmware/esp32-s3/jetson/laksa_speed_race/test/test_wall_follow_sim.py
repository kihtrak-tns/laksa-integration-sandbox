import unittest

from laksa_speed_race.wall_follow_sim import _zero_row


class EvidenceTimingTests(unittest.TestCase):
    def test_obstacle_approach_and_applied_stop_use_separate_windows(self):
        rows = [
            {"sim_time_s": 5.45, "requested_speed_mps": 0.25, "applied_speed_mps": 0.25},
            {"sim_time_s": 7.45, "requested_speed_mps": 0.0, "applied_speed_mps": 0.18},
            {"sim_time_s": 7.57, "requested_speed_mps": 0.0, "applied_speed_mps": 0.0},
        ]
        request_zero = _zero_row(rows, "requested_speed_mps", 1e-6, 5.45, window_s=5.0)
        applied_zero = _zero_row(rows, "applied_speed_mps", 1e-3, 7.45, window_s=2.0)
        self.assertEqual(request_zero["sim_time_s"], 7.45)
        self.assertEqual(applied_zero["sim_time_s"], 7.57)


if __name__ == "__main__":
    unittest.main()

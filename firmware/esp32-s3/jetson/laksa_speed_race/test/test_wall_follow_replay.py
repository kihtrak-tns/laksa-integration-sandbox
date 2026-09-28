import unittest
from pathlib import Path

from laksa_speed_race.wall_follow_replay import replay_fixture


ROOT = Path(__file__).resolve().parents[1]


class ReplayTests(unittest.TestCase):
    def test_synthetic_fixture_replays_without_physical_claim(self):
        result = replay_fixture(ROOT / "test" / "fixtures" / "synthetic_scan_bag_fixture.json")
        self.assertEqual(result["frame_count"], 6)
        self.assertGreater(result["moving_request_count"], 0)
        self.assertEqual(result["real_rplidar_replay"], "PENDING")


if __name__ == "__main__":
    unittest.main()

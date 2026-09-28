import json
from pathlib import Path
import unittest

from laksa_speed_race.wall_follow_core import ControllerConfig, FreshnessConfig
from laksa_speed_race.wall_follow_ros import APPLIED_TOPIC, ODOM_TOPIC, REQUEST_TOPIC, SCAN_TOPIC


ROOT = Path(__file__).resolve().parents[1]


class InterfaceTests(unittest.TestCase):
    def test_every_runtime_topic_is_simulation_namespaced(self):
        for topic in (SCAN_TOPIC, ODOM_TOPIC, REQUEST_TOPIC, APPLIED_TOPIC):
            self.assertTrue(topic.startswith("/sim/laksa/"), topic)
        source = (ROOT / "laksa_speed_race" / "wall_follow_ros.py").read_text(encoding="utf-8")
        self.assertNotIn('"/laksa/command"', source)

    def test_versioned_config_exactly_constructs_runtime_types(self):
        payload = json.loads((ROOT / "config" / "wall_follow_v1.json").read_text(encoding="utf-8"))
        ControllerConfig(**payload["controller"])
        FreshnessConfig(**payload["request_watchdog"])
        self.assertEqual(payload["scope"], "simulation_and_mock_only")


if __name__ == "__main__":
    unittest.main()

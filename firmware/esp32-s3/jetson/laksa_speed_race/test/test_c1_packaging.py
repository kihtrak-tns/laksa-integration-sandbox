"""ROS packaging contracts required by colcon/ament_python."""

from pathlib import Path
from unittest import mock
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def _setup_kwargs(self):
        with mock.patch("setuptools.setup") as setup:
            runpy.run_path(str(ROOT / "setup.py"), run_name="__main__")
        return setup.call_args.kwargs

    def test_data_file_sources_are_relative_for_ament_python(self):
        data_files = self._setup_kwargs()["data_files"]
        for _, sources in data_files:
            for source in sources:
                self.assertFalse(Path(source).is_absolute(), source)

    def test_merged_console_scripts_preserve_both_scopes(self):
        scripts = self._setup_kwargs()["entry_points"]["console_scripts"]
        self.assertIn(
            "c1_historical_replay = laksa_speed_race.historical_replay:main",
            scripts,
        )
        self.assertIn(
            "wall_follow_controller = laksa_speed_race.wall_follow_ros:controller_main",
            scripts,
        )
        self.assertIn(
            "wall_follow_gym_mock = laksa_speed_race.wall_follow_ros:simulator_main",
            scripts,
        )
        self.assertIn(
            "wall_follow_campaign = laksa_speed_race.wall_follow_sim:main",
            scripts,
        )
        self.assertIn(
            "wall_follow_replay = laksa_speed_race.wall_follow_replay:main",
            scripts,
        )


if __name__ == "__main__":
    unittest.main()

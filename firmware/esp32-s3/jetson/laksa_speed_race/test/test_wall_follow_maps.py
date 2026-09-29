import math
import tempfile
import unittest
from pathlib import Path

from laksa_speed_race.wall_follow_maps import (
    CorridorMap,
    campaign_profiles,
    corner_profiles,
    generate_corridor_map,
)
from laksa_speed_race.wall_follow_sim import _minimum_perimeter_sampled_clearance


class MapTests(unittest.TestCase):
    def test_profiles_include_twenty_inch_uncertainty(self):
        widths = {profile.name: profile.width_m for profile in campaign_profiles()}
        self.assertAlmostEqual(widths["continuous_wall_19in"], 19 * 0.0254)
        self.assertAlmostEqual(widths["continuous_wall_20in"], 20 * 0.0254)
        self.assertAlmostEqual(widths["continuous_wall_21in"], 21 * 0.0254)

    def test_rendered_narrow_corridors_are_distinct(self):
        with tempfile.TemporaryDirectory() as root:
            records = [
                generate_corridor_map(profile, Path(root) / profile.name)
                for profile in campaign_profiles()
                if profile.name in {"continuous_wall_19in", "continuous_wall_20in", "continuous_wall_21in"}
            ]
        rendered = {record["name"]: record["rendered_entry_width_m"] for record in records}
        self.assertLess(rendered["continuous_wall_19in"], rendered["continuous_wall_20in"])
        self.assertLess(rendered["continuous_wall_20in"], rendered["continuous_wall_21in"])
        self.assertEqual(
            len({record["files"][record["name"] + ".pgm"] for record in records}),
            3,
        )

    def test_generation_is_byte_deterministic(self):
        profile = CorridorMap("deterministic", 0.508)
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            one = generate_corridor_map(profile, Path(first))
            two = generate_corridor_map(profile, Path(second))
            self.assertEqual(one["files"], two["files"])

    def test_corner_profile_has_free_entry_arc_and_exit(self):
        profile = corner_profiles()[0]
        self.assertTrue(profile.is_free(1.0, profile.entry_y_m))
        self.assertTrue(profile.is_free(3.0, profile.entry_y_m))
        self.assertTrue(profile.is_free(5.0, 4.5))
        self.assertGreater(profile.point_clearance(5.0, 4.5), 0.0)

    def test_corner_inner_edge_can_be_closer_than_all_four_corners(self):
        profile = corner_profiles()[0]
        yaw = math.pi / 4.0
        arc_angle = -math.pi / 4.0
        radial_position = 1.9  # Deliberately biased toward the inside wall.
        body_x = profile.turn_center_x_m + radial_position * math.cos(arc_angle)
        body_y = profile.turn_center_y_m + radial_position * math.sin(arc_angle)
        base_x = body_x - 0.135 * math.cos(yaw)
        base_y = body_y - 0.135 * math.sin(yaw)
        corner_clearances = []
        for along in (-0.284, 0.284):
            for side in (-0.148, 0.148):
                x = body_x + along * math.cos(yaw) - side * math.sin(yaw)
                y = body_y + along * math.sin(yaw) + side * math.cos(yaw)
                corner_clearances.append(profile.point_clearance(x, y))
        perimeter = _minimum_perimeter_sampled_clearance(profile, base_x, base_y, yaw)
        self.assertLess(perimeter, min(corner_clearances) - 0.015)


if __name__ == "__main__":
    unittest.main()

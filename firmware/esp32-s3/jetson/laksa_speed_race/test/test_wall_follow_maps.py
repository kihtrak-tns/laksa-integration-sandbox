import tempfile
import unittest
from pathlib import Path

from laksa_speed_race.wall_follow_maps import CorridorMap, campaign_profiles, generate_corridor_map


class MapTests(unittest.TestCase):
    def test_profiles_include_twenty_inch_uncertainty(self):
        widths = {profile.name: profile.width_m for profile in campaign_profiles()}
        self.assertAlmostEqual(widths["continuous_wall_19in"], 19 * 0.0254)
        self.assertAlmostEqual(widths["continuous_wall_20in"], 20 * 0.0254)
        self.assertAlmostEqual(widths["continuous_wall_21in"], 21 * 0.0254)

    def test_generation_is_byte_deterministic(self):
        profile = CorridorMap("deterministic", 0.508)
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            one = generate_corridor_map(profile, Path(first))
            two = generate_corridor_map(profile, Path(second))
            self.assertEqual(one["files"], two["files"])


if __name__ == "__main__":
    unittest.main()

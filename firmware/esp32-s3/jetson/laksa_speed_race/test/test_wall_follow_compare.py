"""Paired comparisons must catch regressions without counting safe stops as laps."""

from copy import deepcopy
import hashlib
from pathlib import Path
import json
import tempfile
import unittest

from laksa_speed_race.wall_follow_compare import compare


BASELINE = Path(__file__).resolve().parents[1] / "results" / "wall_follow_10mm" / "run_manifest.json"


class CampaignComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    def test_recorded_campaign_pairs_all_cases_without_claiming_laps(self):
        report = compare(self.baseline, deepcopy(self.baseline))
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual(report["matched_cases"], 85)
        self.assertEqual(report["candidate"]["safe_stop"]["completed"], 0)
        self.assertEqual(report["candidate"]["corner_completion"]["completed"], 15)

    def test_collision_and_lost_completion_regress_even_if_verdict_is_stale(self):
        candidate = deepcopy(self.baseline)
        run = next(item for item in candidate["runs"] if item["scenario_class"] == "corridor_traversal")
        run["collision_count"] = 1
        run["completion"] = False
        report = compare(self.baseline, candidate)
        self.assertEqual(report["gate"], "REGRESSION")
        self.assertIn("more_collisions", report["regressions"][0]["reasons"])
        self.assertIn("lost_completion", report["regressions"][0]["reasons"])

    def test_stop_timing_and_clearance_regressions(self):
        candidate = deepcopy(self.baseline)
        run = next(item for item in candidate["runs"] if item["scenario_class"] == "safe_stop")
        run["time_from_stop_request_to_zero_applied_s"] += 0.06
        run["minimum_perimeter_sampled_clearance_m"] -= 0.01
        report = compare(self.baseline, candidate)
        self.assertEqual(report["gate"], "REGRESSION")
        self.assertIn("clearance_drop_over_5mm", report["regressions"][0]["reasons"])
        self.assertIn("increased_time_from_stop_request_to_zero_applied_s", report["regressions"][0]["reasons"])

    def test_changed_map_or_missing_scenario_is_not_a_paired_comparison(self):
        candidate = deepcopy(self.baseline)
        first_map = next(iter(candidate["maps"].values()))
        first_map["files"][next(iter(first_map["files"]))] = "different"
        with self.assertRaisesRegex(ValueError, "map hashes differ"):
            compare(self.baseline, candidate)
        candidate = deepcopy(self.baseline)
        candidate["runs"].pop()
        with self.assertRaisesRegex(ValueError, "scenario keys differ"):
            compare(self.baseline, candidate)

    def test_windows_baseline_requires_proven_newline_equivalence(self):
        baseline = deepcopy(self.baseline)
        candidate = deepcopy(self.baseline)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, record in candidate["maps"].items():
                record["files"] = {"map.pgm": hashlib.sha256(b"P2\n255\n").hexdigest()}
                baseline["maps"][name]["files"] = {
                    "map.pgm": hashlib.sha256(b"P2\r\n255\r\n").hexdigest()
                }
                path = root / name / "map.pgm"
                path.parent.mkdir()
                path.write_bytes(b"P2\n255\n")
            self.assertEqual(compare(baseline, candidate, root)["map_comparison"], "verified_lf_vs_crlf")
            (root / name / "map.pgm").write_bytes(b"P2\n0\n")
            with self.assertRaisesRegex(ValueError, "does not match its manifest"):
                compare(baseline, candidate, root)


if __name__ == "__main__":
    unittest.main()

"""Portable evidence checks for the bounded C1.2d MPPI horizon."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from laksa_speed_race import closed_loop_qualification as qualification


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _short_horizon_artifacts(path: Path, *, steps: int, collision_step: int | None = None) -> None:
    fault = "collision" if collision_step is not None else "qualification_step_limit_reached"
    summary = {
        "simulator_step_count": steps,
        "sim_time_s": steps * qualification.DT_S,
        "dt_s": qualification.DT_S,
        "accepted_drive_requests": steps,
        "duplicate_state_stamp_rejections": 0,
        "state_stamp_mismatch_events": 0,
        "qualification_limit_reached": collision_step is None,
        "qualification_step_limit": qualification.SHORT_HORIZON_STEPS,
        "fault": fault,
        "steps_after_terminal": 0,
        "collision_edges": int(collision_step is not None),
        "off_track_events": 0,
        "invalid_command_events": 0,
        "final_applied_command": {"steering_rad": 0.0, "speed_mps": 0.0},
        "terminal_zero_observed": True,
        "state_stamp_causality_required": True,
    }
    (path / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    telemetry = [
        {
            "state_stamp_ns": 1_000_000_000 + index * 10_000_000,
            "sequence": index,
            "upstream_linear_mps": "0.25",
            "delta_applied_rad": "0.04",
            "physical_feasibility": "true",
            "safety_veto_pass": "true",
        }
        for index in range(1, steps + 1)
    ]
    _write_csv(
        path / "controller_telemetry.csv",
        ["state_stamp_ns", "sequence", "upstream_linear_mps", "delta_applied_rad", "physical_feasibility", "safety_veto_pass"],
        telemetry,
    )
    commands = [
        {
            "step": index,
            "sim_time_s": f"{index * qualification.DT_S:.2f}",
            "requested_steering_rad": "0.04",
            "requested_speed_mps": "0.25",
            "applied_steering_rad": "0.04",
            "applied_speed_mps": "0.25",
            "mission_state": "RUNNING",
        }
        for index in range(1, steps + 1)
    ]
    _write_csv(
        path / "commands.csv",
        ["step", "sim_time_s", "requested_steering_rad", "requested_speed_mps", "applied_steering_rad", "applied_speed_mps", "mission_state"],
        commands,
    )
    trajectory = [
        {
            "step": index,
            "sim_time_s": f"{index * qualification.DT_S:.2f}",
            "x_m": f"{index * 0.002:.3f}",
            "y_m": "0.0",
            "yaw_rad": "0.0",
            "collision": int(index == collision_step),
            "off_track": 0,
        }
        for index in range(1, steps + 1)
    ]
    _write_csv(
        path / "trajectory.csv",
        ["step", "sim_time_s", "x_m", "y_m", "yaw_rad", "collision", "off_track"],
        trajectory,
    )
    events = [] if collision_step is None else [
        {"step": collision_step, "sim_time_s": collision_step * qualification.DT_S, "event": "collision_edge", "value": 1}
    ]
    _write_csv(path / "events.csv", ["step", "sim_time_s", "event", "value"], events)


class ShortHorizonQualificationTests(unittest.TestCase):
    def test_launch_uses_exact_100_step_gym_limit(self):
        command = qualification._launch_command(
            SimpleNamespace(mode="short-horizon", output_dir="/tmp/c1-short")
        )
        self.assertIn("qualification_step_limit:=100", command)
        self.assertIn("include_gym:=true", command)

    def test_validator_accepts_only_clean_100_step_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            _short_horizon_artifacts(path, steps=100)
            evidence = qualification.validate_short_horizon_artifacts(
                path, shutdown={"success": True, "remaining_pids": []}
            )
        self.assertEqual(evidence["outcome"], "CLEAN_LIMIT_REACHED")
        self.assertEqual(evidence["simulator_steps"], 100)
        self.assertEqual(evidence["maximum_simulated_time_s"], 1.0)
        self.assertIsNone(evidence["first_fault"])

    def test_validator_records_early_collision_step(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            _short_horizon_artifacts(path, steps=2, collision_step=2)
            evidence = qualification.validate_short_horizon_artifacts(
                path, shutdown={"success": True, "remaining_pids": []}
            )
        self.assertEqual(evidence["outcome"], "EARLY_FAULT_OR_INVALID_EVIDENCE")
        self.assertEqual(evidence["first_fault"], {"reason": "collision", "step": 2})


if __name__ == "__main__":
    unittest.main()

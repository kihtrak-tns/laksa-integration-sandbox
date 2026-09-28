# Wall-follow milestone status

Simulation results are not physical-car validation. Physical rows require
human-observed evidence tied to installed firmware and autonomy SHAs.

| Gate | State | Tested source / config / map | Date (UTC) | Evidence |
|---|---|---|---|---|
| ORIN CONTRACT REVIEW | PASS | `orin-bringup@c3a64a630166e1608a2e0e0699d5ac67be89ca6b`; sandbox base `21588774eef8023811e751019b13abc9a43b692e` | 2026-09-28 | [`orin_bringup_contract_review.md`](../integration/orin_bringup_contract_review.md) |
| SIM MODEL | PASS | source `72fe7464a2e6d0c4fcfc6b788ac191682c46ea2f`; config SHA-256 `b1fa0b84e1b36a947eae3f59dfb55651fc50a74684aa6534b4280e14698913e7`; Gym `bdaec1420c3b0f103858d289866d0d4e2e597c30` | 2026-09-28 | 75/75 nominal 20 Hz-control runs passed: 60 corridor traversals and 15 corner completions; minimum full-body clearance 0.0483 m; [`run_manifest.json`](../../firmware/esp32-s3/jetson/laksa_speed_race/results/wall_follow_20hz/run_manifest.json) |
| WALL FOLLOWER | PASS (SIM ONLY) | same source/config; 100 Hz Gym, 20 Hz scan/request; target 0.254 m; 19/20/21/30-inch corridors plus 90-degree corner | 2026-09-28 | 15/15 focused tests passed, including opening+obstacle priority; 60/60 corridors and 15/15 corners completed without collision. Race-lap completion is `UNVERIFIED` (0 lap runs). |
| FAULT/STOP TESTS | PASS (SIM ONLY) | same source/config; independent 0.2 s request watchdog | 2026-09-28 | 10/10 injected cases passed, including delayed/dropped scans and opening+obstacle; zero applied in 0.12-0.44 s, simulated stop distance 0.015-0.134 m; CSV traces committed |
| REAL SCAN REPLAY | PARTIAL / BLOCKED | synthetic analytic fixture passed; no committed real `/scan` bag at reviewed Orin head | 2026-09-28 | [`synthetic_replay.json`](../../firmware/esp32-s3/jetson/laksa_speed_race/results/wall_follow_20hz/synthetic_replay.json); real replay pending A2/A6 evidence |
| WHEELS-UP | BLOCKED | Physical work excluded by issue #2 | 2026-09-28 | Requires human-run installed-car gate |
| LOW-SPEED CAR | BLOCKED | Physical work excluded by issue #2 | 2026-09-28 | Requires prior contract, stop, and wheels-up evidence |

Current blockers: no committed Orin results, no real RPLIDAR bag/contract,
unverified installed-firmware wire layout, speed/eRPM conversion, asymmetric
steering limits, brake/timeout behavior, wired RJ45 stop, or final command
publisher ownership. The Rules Guardian's historical Teensy authority also
conflicts with the installed ESP32-S3/VESC path and must be resolved before
promotion. Docker and ROS 2 Humble were unavailable on both Windows and local
Ubuntu-22.04 WSL, so the ROS launch, ROS-observed frequencies, and ROS terminal
collision/reset behavior remain `UNVERIFIED`.

The earlier 100 Hz-controller evidence remains preserved under
`results/wall_follow` for comparison. Current acceptance evidence is under
`results/wall_follow_20hz`; neither result set is a race lap or physical-car
validation.

Next action: on a Docker/ROS 2 Humble host, reproduce the isolated ROS launch;
then have the hardware owner commit a real RPLIDAR bag and exact TF/driver
configuration for read-only replay. Do not connect this controller to the car.

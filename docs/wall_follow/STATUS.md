# Wall-follow milestone status

Simulation results are not physical-car validation. Physical rows require
human-observed evidence tied to installed firmware and autonomy SHAs.

| Gate | State | Tested source / config / map | Date (UTC) | Evidence |
|---|---|---|---|---|
| ORIN CONTRACT REVIEW | PASS | `orin-bringup@c3a64a630166e1608a2e0e0699d5ac67be89ca6b`; sandbox base `21588774eef8023811e751019b13abc9a43b692e` | 2026-09-28 | [`orin_bringup_contract_review.md`](../integration/orin_bringup_contract_review.md) |
| SIM MODEL | PASS | source `e34eb13ea952802135530d2e02c555beaa6eb57f`; config SHA-256 `7597ea51333d9e9cb6a15f3c2f807ba9666aa4b25d09e77695a564aaaee04ea0`; Gym `bdaec1420c3b0f103858d289866d0d4e2e597c30` | 2026-09-28 | 60/60 nominal runs passed: 4 maps x 5 seeds x 3 poses; minimum full-body clearance 0.0483 m; [`run_manifest.json`](../../firmware/esp32-s3/jetson/laksa_speed_race/results/wall_follow/run_manifest.json) |
| WALL FOLLOWER | PASS (SIM ONLY) | same source/config; target 0.254 m; 19/20/21/30-inch generated corridors | 2026-09-28 | Bounded finite scan-only requests, right/left sign tests, doorway recess traversal, no collisions; 13/13 focused unit tests passed |
| FAULT/STOP TESTS | PASS (SIM ONLY) | same source/config; independent 0.2 s request watchdog | 2026-09-28 | 8/8 injected cases passed; zero applied in 0.12-0.44 s, simulated stop distance 0.015-0.134 m; CSV traces committed |
| REAL SCAN REPLAY | PARTIAL / BLOCKED | synthetic analytic fixture passed; no committed real `/scan` bag at reviewed Orin head | 2026-09-28 | [`synthetic_replay.json`](../../firmware/esp32-s3/jetson/laksa_speed_race/results/wall_follow/synthetic_replay.json); real replay pending A2/A6 evidence |
| WHEELS-UP | BLOCKED | Physical work excluded by issue #2 | 2026-09-28 | Requires human-run installed-car gate |
| LOW-SPEED CAR | BLOCKED | Physical work excluded by issue #2 | 2026-09-28 | Requires prior contract, stop, and wheels-up evidence |

Current blockers: no committed Orin results, no real RPLIDAR bag/contract,
unverified installed-firmware wire layout, speed/eRPM conversion, asymmetric
steering limits, brake/timeout behavior, wired RJ45 stop, or final command
publisher ownership. The Rules Guardian's historical Teensy authority also
conflicts with the installed ESP32-S3/VESC path and must be resolved before
promotion.

Next action: on a Docker/ROS 2 Humble host, reproduce the isolated ROS launch;
then have the hardware owner commit a real RPLIDAR bag and exact TF/driver
configuration for read-only replay. Do not connect this controller to the car.

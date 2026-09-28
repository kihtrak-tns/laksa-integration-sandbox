# Wall-follow milestone status

Simulation results are not physical-car validation. Physical rows require
human-observed evidence tied to installed firmware and autonomy SHAs.

| Gate | State | Tested source / config / map | Date (UTC) | Evidence |
|---|---|---|---|---|
| ORIN CONTRACT REVIEW | PASS | `orin-bringup@c3a64a630166e1608a2e0e0699d5ac67be89ca6b`; sandbox base `21588774eef8023811e751019b13abc9a43b692e` | 2026-09-28 | [`orin_bringup_contract_review.md`](../integration/orin_bringup_contract_review.md) |
| UPDATED BASE INTEGRATION | PASS | merge `92ed803cdb9e331312139b888c6da4ebf195f25f`; base `f9676915ff71d3e7f22ed588e8054e5ce7cf9c72` | 2026-09-28 | The sole content conflict was `setup.py`; resolution preserves the base's `c1_historical_replay` and all wall-follow simulation entry points. Focused post-merge checks: 23/23 passed. [`Integration record`](base_integration_2026-09-28.md) |
| SIM MODEL | PASS | source `290a2f3b22b3dc12443535fec7d2545e47ca5dcf`; config SHA-256 `b1fa0b84e1b36a947eae3f59dfb55651fc50a74684aa6534b4280e14698913e7`; Gym `bdaec1420c3b0f103858d289866d0d4e2e597c30` | 2026-09-28 | 75/75 nominal 20 Hz-control runs passed with zero collisions. Rendered 19/20/21-inch widths are distinct at 0.48/0.50/0.54 m. Minimum perimeter-sampled clearance estimate 0.0483 m. [`Current manifest`](../../firmware/esp32-s3/jetson/laksa_speed_race/results/wall_follow_10mm/run_manifest.json) |
| WALL FOLLOWER | PASS (GYM ONLY) | same source/config; 100 Hz Gym, 20 Hz scan/request; 10 mm maps | 2026-09-28 | 19/19 focused tests passed. 60/60 corridors and 15/15 corners completed; all 85 manifest records passed collision, width, clearance, stop-reason, completion-class, and obstacle-timing audit. Race-lap completion remains `UNVERIFIED`. |
| FAULT/STOP TESTS | PARTIAL | same source/config; independent 0.2 s request watchdog | 2026-09-28 | Gym: 10/10 passed. Both obstacle cases safely stopped without completion/collision; detection-to-stop request 2.00/2.35 s, stop-request-to-zero-applied 0.12 s, post-request distance 0.0156/0.0153 m. ROS terminal/collision/restart behavior remains `UNVERIFIED`. |
| REAL SCAN REPLAY | PARTIAL / BLOCKED | synthetic analytic fixture passed; no committed real `/scan` bag at reviewed Orin head | 2026-09-28 | [`synthetic_replay.json`](../../firmware/esp32-s3/jetson/laksa_speed_race/results/wall_follow_10mm/synthetic_replay.json); real replay pending A2/A6 evidence |
| WHEELS-UP | BLOCKED | Physical work excluded by issue #2 | 2026-09-28 | Requires human-run installed-car gate |
| LOW-SPEED CAR | BLOCKED | Physical work excluded by issue #2 | 2026-09-28 | Requires prior contract, stop, and wheels-up evidence |

Current blockers: no committed Orin results, no real RPLIDAR bag/contract,
unverified installed-firmware wire layout, speed/eRPM conversion, asymmetric
steering limits, brake/timeout behavior, wired RJ45 stop, or final command
publisher ownership. The Rules Guardian's historical Teensy authority also
conflicts with the installed ESP32-S3/VESC path and must be resolved before
promotion. Docker and ROS 2 Humble were unavailable on both Windows and local
Ubuntu-22.04 WSL. A discovered Ubuntu host at `192.168.1.236` did not accept an
SSH connection before the bounded timeout, so its runtime could not be
inspected or used. The ROS launch, ROS-observed frequencies, and ROS terminal
collision/reset behavior remain `UNVERIFIED`.

Review fixes on this branch latch a terminal mock episode, render 10 mm maps,
sample the body perimeter for clearance estimates, and separately time first
obstacle detection, first stop request, and zero applied speed. Verification:
19 focused Python tests, `compileall`, and the full pinned-Gym campaign passed.
The ROS mock requires a launch restart to reset both Gym and controller after
collision or terminal completion, but this behavior has not run on Humble.
After merging the updated speed-race base, 23 focused packaging, isolation, and
wall-follow tests passed. The full Windows pytest collection reported 48 pass,
8 Linux-only skips, 18 failures downstream of frozen course/raceline hashes in
the CRLF checkout, and one initial packaging failure because the ignored test
environment lacked `setuptools`. The focused packaging test passed after that
declared build dependency was installed; the other failures are recorded rather
than hidden.

Earlier evidence remains preserved under `results/wall_follow` and
`results/wall_follow_20hz`. Current 10 mm acceptance evidence is under
`results/wall_follow_10mm`. None is a race lap or physical-car validation.

Next action: on a Docker/ROS 2 Humble host, reproduce the isolated ROS launch,
measure scan/request rates, force collision, verify terminal latching, and
restart into a fresh episode. Then have the hardware owner commit a real
RPLIDAR bag and exact TF/driver configuration for read-only replay. Do not
connect this controller to the car.

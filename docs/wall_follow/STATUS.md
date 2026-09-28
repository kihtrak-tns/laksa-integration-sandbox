# Wall-follow milestone status

Simulation results are not physical-car validation. Physical rows require
human-observed evidence tied to installed firmware and autonomy SHAs.

| Gate | State | Tested source / config / map | Date (UTC) | Evidence |
|---|---|---|---|---|
| ORIN CONTRACT REVIEW | PASS | `orin-bringup@c3a64a630166e1608a2e0e0699d5ac67be89ca6b`; sandbox base `21588774eef8023811e751019b13abc9a43b692e` | 2026-09-28 | [`orin_bringup_contract_review.md`](../integration/orin_bringup_contract_review.md) |
| SIM MODEL | PARTIAL | New code `fad750f4e5fff5c825a8ce5214896c8f9d72d6c4` pending Gym rerun; historical evidence: `72fe7464a2e6d0c4fcfc6b788ac191682c46ea2f`, config SHA-256 `b1fa0b84e1b36a947eae3f59dfb55651fc50a74684aa6534b4280e14698913e7`, Gym `bdaec1420c3b0f103858d289866d0d4e2e597c30` | 2026-09-28 | Historical 75/75 nominal 20 Hz runs at old source; the 1 cm maps and perimeter metric have no Gym results yet. [`Prior manifest`](../../firmware/esp32-s3/jetson/laksa_speed_race/results/wall_follow_20hz/run_manifest.json) |
| WALL FOLLOWER | PARTIAL | New code `fad750f4e5fff5c825a8ce5214896c8f9d72d6c4` pending Gym rerun; old config above | 2026-09-28 | 18/18 focused tests passed locally, including terminal authority and distinct rendered widths. Historical 60/60 corridors and 15/15 corners apply only to old source/map hashes. Race-lap completion `UNVERIFIED`. |
| FAULT/STOP TESTS | PARTIAL | New code `fad750f4e5fff5c825a8ce5214896c8f9d72d6c4` pending Gym and ROS rerun | 2026-09-28 | Historical 10/10 injected Gym cases apply only to old source. New terminal latch and first-hazard timing have focused Python checks but no ROS execution. |
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

Review fixes on this branch now latch a terminal mock episode, increase map
resolution so 19/20/21-inch corridors rasterize distinctly, sample the body
perimeter for clearance estimates, and time obstacle response from first entry
into the slowdown zone. Local verification: 18 focused Python tests and
`compileall` passed. F1TENTH Gym, ROS 2, and Docker are absent in this
workspace; no new campaign result is claimed. The ROS mock requires a launch
restart to reset both Gym and controller after collision or terminal completion.

The earlier 100 Hz-controller evidence remains preserved under
`results/wall_follow` for comparison. Current acceptance evidence is under
`results/wall_follow_20hz`; both are historical results at their recorded
source/map revisions, and neither is a race lap or physical-car validation.

Next action: rerun the full 20 Hz Gym campaign with the new source and record
new config/map hashes and perimeter-clearance estimates. On a Docker/ROS 2
Humble host, reproduce the isolated ROS launch and terminal behavior;
then have the hardware owner commit a real RPLIDAR bag and exact TF/driver
configuration for read-only replay. Do not connect this controller to the car.

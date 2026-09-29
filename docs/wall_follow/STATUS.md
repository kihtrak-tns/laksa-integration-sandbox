# Wall-follow milestone status

Simulation results are not physical-car validation. Physical rows require
human-observed evidence tied to installed firmware and autonomy SHAs.

| Gate | State | Tested source / config / map | Date (UTC) | Evidence |
|---|---|---|---|---|
| ORIN CONTRACT REVIEW | PASS (PHASE A EVIDENCE REVIEW) | `orin-bringup@2f1306072a4fe828412585b056ec8af1243e3056` | 2026-09-28 | A1a 97/97 ALL MATCH; A1b 6/6 with battery unplugged; A2 accepted stable 12.8 Hz / 1,800 beams; A3 boot services and A5 ZED pipeline recorded; A6 static and hand-carried bags recorded. Hand-carried motion is not a vehicle run. Remaining physical blockers are retained. [`Source-linked contract review`](../integration/orin_bringup_contract_review.md) |
| UPDATED BASE INTEGRATION | PASS | merge `92ed803cdb9e331312139b888c6da4ebf195f25f`; base `f9676915ff71d3e7f22ed588e8054e5ce7cf9c72` | 2026-09-28 | The sole content conflict was `setup.py`; resolution preserves the base's `c1_historical_replay` and all wall-follow simulation entry points. Focused post-merge checks: 23/23 passed. [`Integration record`](base_integration_2026-09-28.md) |
| SIM MODEL | PASS | source `290a2f3b22b3dc12443535fec7d2545e47ca5dcf`; config SHA-256 `b1fa0b84e1b36a947eae3f59dfb55651fc50a74684aa6534b4280e14698913e7`; Gym `bdaec1420c3b0f103858d289866d0d4e2e597c30` | 2026-09-28 | 75/75 nominal 20 Hz-control runs passed with zero collisions. Rendered 19/20/21-inch widths are distinct at 0.48/0.50/0.54 m. Minimum perimeter-sampled clearance estimate 0.0483 m. [`Current manifest`](../../firmware/esp32-s3/jetson/laksa_speed_race/results/wall_follow_10mm/run_manifest.json) |
| WALL FOLLOWER | PASS (GYM ONLY) | same source/config; 100 Hz Gym, 20 Hz scan/request; 10 mm maps | 2026-09-28 | 19/19 focused tests passed. 60/60 corridors and 15/15 corners completed; all 85 manifest records passed collision, width, clearance, stop-reason, completion-class, and obstacle-timing audit. Race-lap completion remains `UNVERIFIED`. |
| FAULT/STOP TESTS | PARTIAL | same source/config; independent 0.2 s request watchdog | 2026-09-28 | Gym: 10/10 passed. Both obstacle cases safely stopped without completion/collision; detection-to-stop request 2.00/2.35 s, stop-request-to-zero-applied 0.12 s, post-request distance 0.0156/0.0153 m. Humble observed a forced `gym_collision`, unchanged steps through a 20-message moving probe, and a distinct active episode after restart. Direct applied-motion output and the restarted episode's initial step count were not captured. |
| ROS 2 HUMBLE SIMULATION | PARTIAL / UNVERIFIED | Saved checkout SHA `b6f5bd0a799e594ea4a47b1ade4179e0586c7d22` (build link unproven); collision image `sha256:d128d8d010d1b175a85ec6a97836274ac5c8685008b3bc180382343e4eaac233` (build source mapping not proven) | 2026-09-28 | Rebuilt service scan observed 19.969–19.995 Hz in ten windows. A separate collision launch logged `gym_collision` at step 1; after 20 moving probes, same episode stayed at step 1 and rejection count rose 105. Restart logged a distinct active episode ID. The Dell operator now reports ten `/sim/laksa/motion_request` windows at 19.968–19.996 Hz on `wall-follow`. The captured checkout SHA and collision-container image ID still lack a build-time association; exact image identity for the rate container was not captured. [`ROS gate record and saved evidence`](ros_humble_gate.md) |
| REAL SCAN REPLAY | UNVERIFIED | synthetic adapter preflight `d325f12ed721e407d9e2a2b6f23607e3d8fc6585`; Orin bags `20260928_033352_static` and `20260928_034706_handcarried` | 2026-09-28 | Added verbatim serialized `/scan` exporter and scan-only replay procedure. Five adapter/export tests pass; preflight bounds 12 synthetic scans at 12.8 Hz and verifies invalid/stale stops. A6 export and measured laser-to-base transform are unavailable, so no real replay is claimed. [`Replay path and preflight`](integration_gate.md#read-only-laserscan-export-and-replay) |
| WHEELS-UP | BLOCKED | Physical work excluded by issue #2 | 2026-09-28 | Requires human-run installed-car gate |
| LOW-SPEED CAR | BLOCKED | Physical work excluded by issue #2 | 2026-09-28 | Requires prior contract, stop, and wheels-up evidence |

Current blockers: the Dell operator terminal can build and run the isolated
Humble Docker image, but this restricted runner still cannot access its Docker
socket. The ROS gate is `PARTIAL / UNVERIFIED`: rebuilt-service scan publication, a
forced Gym collision, unchanged Gym steps through a moving-request probe, a
fresh episode after restart, and request-rate measurements were observed. The
rate-test image and build checkout are not linked by captured provenance. The two A6 bags
remain on the Orin; no scan-only export or measured laser-to-base transform
was available in this session, so real replay is also `UNVERIFIED`. Phase A
results now exist at the exact Orin SHA recorded above; they establish
read-only interface/sensor observations, not physical drive, braking, or
autonomy validation. Remaining blockers include micro-ROS session churn and
silent stalls, speed/eRPM conversion, powered steering direction/endpoints,
physical stop/brake/timeout behavior, wired RJ45 stop, a measured TF contract,
and final single command publisher ownership. The Rules Guardian's historical
Teensy authority also conflicts with the installed ESP32-S3/VESC path and must
be resolved before promotion.

Review fixes on this branch latch a terminal mock episode, render 10 mm maps,
sample the body perimeter for clearance estimates, and separately time first
obstacle detection, first stop request, and zero applied speed. Verification:
19 focused Python tests, `compileall`, and the full pinned-Gym campaign passed.
The ROS mock requires a launch restart to reset both Gym and controller after
collision or terminal completion. Forced collision and a fresh-episode restart have now been observed on
Humble.
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

The operator has supplied Dell evidence for the deterministic collision,
post-collision moving-request probe, and a distinct active episode after
restart. Details and compact logs are in [`ros_humble_gate.md`](ros_humble_gate.md).
The ROS gate remains `PARTIAL / UNVERIFIED` until the tested image is tied
to a clean source checkout by build provenance. The probe has no direct
applied-motion trace or initial restart step count. Separately export only
`/scan` from the A6 hand-carried bag and provide the measured LiDAR transform
for read-only replay. Do not connect this controller to the car.

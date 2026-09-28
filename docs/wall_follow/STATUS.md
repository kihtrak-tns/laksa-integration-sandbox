# Wall-follow milestone status

Simulation results are not physical-car validation. Physical rows require
human-observed evidence tied to installed firmware and autonomy SHAs.

| Gate | State | Tested source / config / map | Date (UTC) | Evidence |
|---|---|---|---|---|
| ORIN CONTRACT REVIEW | PASS | `orin-bringup@c3a64a630166e1608a2e0e0699d5ac67be89ca6b`; sandbox base `21588774eef8023811e751019b13abc9a43b692e` | 2026-09-28 | [`orin_bringup_contract_review.md`](../integration/orin_bringup_contract_review.md) |
| SIM MODEL | NOT STARTED | — | 2026-09-28 | Model card and run manifest pending |
| WALL FOLLOWER | NOT STARTED | — | 2026-09-28 | Controller and mock interface pending |
| FAULT/STOP TESTS | NOT STARTED | — | 2026-09-28 | Fault matrix and stop metrics pending |
| REAL SCAN REPLAY | BLOCKED | No committed real `/scan` bag at reviewed Orin head | 2026-09-28 | Synthetic fixture planned; real replay pending A2/A6 evidence |
| WHEELS-UP | BLOCKED | Physical work excluded by issue #2 | 2026-09-28 | Requires human-run installed-car gate |
| LOW-SPEED CAR | BLOCKED | Physical work excluded by issue #2 | 2026-09-28 | Requires prior contract, stop, and wheels-up evidence |

Current blockers: no committed Orin results, no real RPLIDAR bag/contract,
unverified installed-firmware wire layout, speed/eRPM conversion, asymmetric
steering limits, brake/timeout behavior, wired RJ45 stop, or final command
publisher ownership. The Rules Guardian's historical Teensy authority also
conflicts with the installed ESP32-S3/VESC path and must be resolved before
promotion.

Next action: implement the isolated scan-capable Gym boundary, model card,
mock motion-request interface, controller core, and reproducible simulation
tests without any physical command topic.

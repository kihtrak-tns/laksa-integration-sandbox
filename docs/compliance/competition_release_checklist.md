# LAKSA 2026 Competition Release Checklist

Record evidence links and reviewer initials against a specific public repository tag/commit. An unchecked blocking item prevents a competition-ready claim.

## Source and repository

- [ ] Rulebook revision/date/checksum match `source_manifest.json`.
- [ ] Official SharePoint archive was checked for a newer revision.
- [ ] All relied-upon organizer clarifications are archived and reflected in the register.
- [ ] Competition release exists in the public `Project-LAKSA/Project_LAKSA` repository.
- [ ] Caterpillar proprietary IP/dependencies/data audit is signed off.

## Required milestones and safety

- [ ] August 14 demo evidence shows forward motion, controlled 90° turn, and forward motion afterward.
- [ ] Safety-review date and heartbeat requirement are confirmed.
- [ ] Course RJ45 schematic and pinout are reviewed.
- [ ] RUN continuity, STOP isolation, cable disconnect, open wire, invalid state, and MCU-reset tests fail safe.
- [ ] Propulsion stop latency and stop distance are measured at approved speeds.
- [ ] Steering after E-stop is bounded and returns neutral after stopping.
- [ ] Safe E-stop clear/resume behavior is validated without remote control.
- [ ] Jetson command loss/staleness neutralizes propulsion.
- [ ] Jetson shutdown/reboot and Teensy reset tests are complete.

## Autonomous competition behavior

- [ ] Competition mode rejects RC, Xbox, Wi-Fi, Bluetooth, dashboard, and other off-track control commands.
- [ ] Radio/telemetry configuration matches the organizer answer to `CLAR-003`.
- [ ] Visual start passes representative positive, negative, stale, and false-start tests.
- [ ] Three-lap speed-course counting and autonomous stop are validated.
- [ ] Two-lap obstacle-course counting and autonomous stop are validated.
- [ ] Ten-minute heat termination behavior is safe.
- [ ] Manual-start fallback, if retained, matches organizer guidance.
- [ ] Course mapping/teach strategy matches organizer guidance.

## Physical and power evidence

- [ ] Complete race configuration is ≤16 in wide, ≤24 in long, and ≤16 in high at all relevant steering/suspension positions.
- [ ] Race-ready robot is ≤25 lb.
- [ ] Every onboard rail and maximum charged battery voltage is <50 V.
- [ ] Batteries, regulators, wiring, fuses/protection, mounts, and strain relief pass inspection.
- [ ] Three consecutive heats are supported by measured runtime/energy evidence.
- [ ] Ten-minute thermal/load test passes for compute, regulators, motor control, and sensors.
- [ ] Flag mount is ≤8 in above ground; top of flag is 24–26 in; only permitted flag/wire exemption is used.

## Release and operations

- [ ] Frozen calibration/configuration is archived with the release.
- [ ] ZED/RPLIDAR transforms and health thresholds are recorded.
- [ ] Pre-run inspection and competition-mode lockout checklist is rehearsed.
- [ ] Primary and backup E-stop operators are assigned and trained.
- [ ] Intervention, retrieval, resume, and early-end callouts are rehearsed.
- [ ] Logs, video, fault records, and evidence index are retained.
- [ ] Final Rules Guardian review has no blocking finding.
- [ ] Team reviewer and captain approve the release.

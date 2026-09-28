# Orin bring-up contract review (read-only Phase 0)

## Review identity and scope

- Reviewed repository: `kihtrak-tns/orin-bringup`
- Reviewed committed head: `c3a64a630166e1608a2e0e0699d5ac67be89ca6b`
- Review date: 2026-09-28 UTC
- Sandbox base: `competition/speed-race-track@21588774eef8023811e751019b13abc9a43b692e`
- Scope: committed files only. No SSH to the Orin, ROS graph access, hardware command, bring-up execution, or edit to `orin-bringup` occurred.

At the reviewed head, `STATUS.md:10-18` still marks A1a, A1b, A2, A3, A5,
and A6 `not started`. There is no committed `results/` directory. The repository
itself says it was built without a link to the car or Orin and has not run on
real hardware (`README.md:8-12`), and that it has only received Python syntax
checks rather than a ROS/colcon build (`README.md:82-86`). Statements in code
comments about earlier live observations are therefore treated as claimed
provenance, not as committed test evidence.

`AGENTS.md` is a symlink-style pointer to `CLAUDE.md`. That file requires
hardware results to be committed under `results/` and forbids inferring or
advancing gated hardware work without them (`CLAUDE.md:54-94,96-140`). It also
references `orin_bringup_plan.md` and `esp32_installed_firmware_findings.md`,
but neither file is committed at this head (`CLAUDE.md:8,58-60`). A shareable,
versioned copy is required before physical integration if it contains contract
details not captured by committed source.

## Contract and evidence matrix

| Interface / safety item | Code present | Claimed intent | Actual committed test or human evidence | Unresolved dependency for physical integration |
|---|---|---|---|---|
| ESP32 firmware message layout and QoS | `DriveCommand`, `VescState`, `Pca9685State`, and `VehicleState` are reconstructed from mixed public branches (`README.md:28-47`; `src/laksa_interfaces/package.xml:5-11`). State subscribers use BEST_EFFORT/KEEP_LAST(1)/VOLATILE (`laksa_readonly_check.py:42-55`; `laksa_health.py:21-33`); the loopback uses RELIABLE commands and BEST_EFFORT state (`drive_command_loopback_test.py:52-68`). | Match flashed `cba74e7-dirty`, with raw CDR cross-check before trusting typed data (`laksa_readonly_check.py:2-28`). | None committed: A1a/A1b not started and no `results/`. The README explicitly says public source is not proof of flashed wire layout (`README.md:42-47`). | Run A1a against the installed firmware, retain raw/typed evidence, then run human-gated A1b with battery physically unplugged. Obtain the missing versioned firmware findings. |
| `/scan` frame, angles, rate, and timestamps | No LiDAR driver, `LaserScan` configuration, frame declaration, or scan QoS is committed. The bag launcher merely lists `/scan` among topics to record (`src/laksa_bringup/launch/record_bags.launch.py:1-36`). | Slamtec A2M12 via `sllidar_ros2`, planned but not installed (`docs/dependencies.md:15`; `README.md:88-101`). | None committed: A2 and A6 not started; no bag or `results/`. | Measure and commit frame ID, mounting transform, angle direction/range/increment, range limits, scan rate, timestamp clock/source, QoS, and dropout behavior from the installed unit. |
| Odometry and TF | `VescState` exposes tachometer, angular velocities, and `vehicle_linear_velocity_mps`; `VehicleState` exposes IMU and steering fields (`src/laksa_interfaces/msg/VescState.msg:4-31`; `VehicleState.msg:2-12`). No odometry publisher, localization node, or TF broadcaster is committed. | State telemetry is available for later integration; this repository does not claim an odometry/TF solution. | None committed. No A2/A5/A6 results and no ROS graph capture. | Define and verify `map`/`odom`/`base_link`/scan frames, wheel-odometry conversion, covariance, timestamp ownership, and TF authority. Simulation uses its own `/sim/laksa/*` frames and must not imply the car contract is known. |
| `DriveCommand` units, sign, and brake | `float32 speed_mps`, `float32 steering_angle_rad`, `bool brake`; positive steering is documented as left and brake as active VESC regenerative/current braking (`src/laksa_interfaces/msg/DriveCommand.msg:1-10`). The loopback checks steering echo, zero requested eRPM, brake state, and command freshness (`drive_command_loopback_test.py:24-37,151-195`). | SI vehicle-level request; positive-left steering; explicit brake request. | None committed: A1b not started. No proof that the flashed binary matches the definition, sign convention, or brake semantics. | A1a/A1b evidence, wheels-up sign observation, brake/coast characterization, and installed-firmware SHA. The simulation mock may use these provisional SI semantics but must not publish `/laksa/command`. |
| VESC speed/eRPM conversion | `VescState` exposes requested/active/measured eRPM and derived angular/linear velocities (`VescState.msg:9-31`). | Firmware converts vehicle speed requests to VESC behavior. | No committed conversion test. The README labels speed/odometry scaling a placeholder until measured (`README.md:95-97,105-110`); the loopback deliberately uses zero speed to avoid it (`drive_command_loopback_test.py:24-30,169-176`). | Measure forward/reverse speed-to-eRPM scaling, gearing/wheel radius, deadband, saturation, braking, and odometry factor. |
| Steering limits | Teleop exposes a symmetric `max_abs_steer_rad=0.6458` placeholder derived from uncommitted findings (`supervisor_node.py:62-71`). | Clamp and slew steering before a manual request reaches the command topic (`supervisor_node.py:93-100,154-164`). | No committed physical endpoint or sign result. A1b and later physical gates are not started. | Remeasure complete vehicle and safe asymmetric endpoints. Do not substitute the older proxy's `+0.523/-0.288 rad` or the teleop placeholder for installed-car calibration. |
| Timeout and loss-of-agent behavior | Loopback expects a firmware 500 ms command timeout and checks `command_fresh` after publisher silence (`drive_command_loopback_test.py:24-37,189-195`). The agent systemd unit restarts on failure (`laksa-microros-agent.service:19-29`); teleop uses a 0.2 s Joy timeout and explicit brake when enabled (`supervisor_node.py:62-71,102-145`). | Stale requests brake/center in firmware; host agent and health services recover independently; disabled teleop stays inert. | No committed timeout, loss-of-agent, braking-distance, or reboot result. A1b/A3 not started. | Measure ESP32/VESC response to publisher silence, frozen messages, USB/agent loss, process crash, and restart. Confirm whether timeout means coast, regenerative braking, or another action at each speed. |
| Wired RJ45 course stop | No RJ45 stop interface, GPIO input, service, state, or test exists in `orin-bringup`. Health boot explicitly starts no command publisher (`health.launch.py:1-23`). | Not established by this repository. | None committed. | Design and test the rulebook rev 4.2 closed=RUN/open=STOP wired course interface, independent of Jetson/ROS. Record continuity, open-wire, disconnect, stop latency/distance, and bounded steering evidence. |
| Final publisher ownership | Loopback and teleop can each publish `/laksa/command` (`drive_command_loopback_test.py:101-108`; `supervisor_node.py:79-80`). Teleop defaults disabled and returns before publishing (`supervisor_node.py:83-109`); no systemd unit starts it (`README.md:62-68`). | Exactly one command publisher; teleop is a manual Joy publisher with deadman, not an autonomy arbiter (`CLAUDE.md:33-36,125-129`). | No committed ROS graph or publisher-ownership test. A3 not started. | Select and verify one final arbitration/authority process, prove other publishers are disabled/rejected, and integrate the wired stop and firmware safety gates before any autonomy adapter is enabled. Wall following ends at a mock motion-request interface. |

## Architecture conflict and disposition

The sandbox Rules Guardian at
`origin/codex/rules-guardian-v1@03dfca2e00ffabb6b598c66a1b78cae477333443`
uses rulebook rev 4.2 and treats a Teensy 4.1 as the intended competition
safety/actuation authority. The installed-car evidence represented by
`orin-bringup@c3a64a6` instead targets an ESP32-S3 over USB micro-ROS and a
VESC. The older Teensy architecture is historical guidance, not authority to
override current measured hardware; the ESP32 implementation is likewise not
competition-approved merely because code exists. This conflict blocks car
promotion, not isolated simulation.

Rules disposition for this Phase 0 scope: **ALLOW WITH CONDITIONS**. Simulation
and mock-interface work is allowed because it cannot command physical
actuation. Rules 1.1, 1.2, 1.2.9, 2.2.1, 2.4, 2.5, 3.1-3.3, 3.6, and 3.7
remain `OPEN_EVIDENCE`/`OPEN_DESIGN` or otherwise unresolved for physical
promotion. No simulation result may be labeled car validation or competition
compliance.

## Simulation contract allowed after this gate

The wall follower may use an internal mock request with:

- speed in metres per second;
- positive steering in radians to the left;
- an explicit stop/brake intent flag whose simulated deceleration is not
  claimed to represent VESC regenerative braking;
- dedicated `/sim/laksa/*` topics and frames only;
- an independent freshness/watchdog gate that continues stepping Gym toward a
  stop after command loss.

Ground-truth pose and map data are metrics-only. No `/laksa/command`,
`/cmd_vel`, VESC, GPIO, micro-ROS, production Orin service, SSH session, or
automatic car enable path is authorized.

## Pending inputs before car integration

1. A versioned, shareable `orin_bringup_plan.md` and
   `esp32_installed_firmware_findings.md` if their missing details remain
   authoritative.
2. Committed A1a/A1b/A2/A3/A5/A6 result files from the exact installed firmware
   and Orin source revisions.
3. A real RPLIDAR `/scan` bag with its transform, driver configuration, QoS,
   and clock provenance.
4. Measured speed/eRPM, steering sign/endpoints, brake/coast, timeout,
   loss-of-agent, and stop-distance results.
5. A reviewed single-publisher command authority and independent wired RJ45
   course-stop design/evidence.


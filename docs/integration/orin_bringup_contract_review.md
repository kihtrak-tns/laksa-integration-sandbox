# Orin bring-up contract review (source-linked Phase A evidence)

## Review identity and scope

- Repository: [`kihtrak-tns/orin-bringup`](https://github.com/kihtrak-tns/orin-bringup)
- Exact reviewed commit: `2f1306072a4fe828412585b056ec8af1243e3056`
- Review date: 2026-09-28 UTC
- Scope: committed status, result records, installed-firmware findings, and
  micro-ROS link note at that commit. The referenced physical work was already
  performed by its named human operator; this review does not repeat or extend
  it. No Orin files were edited.

Primary evidence read at that SHA:

- [`STATUS.md`](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/STATUS.md)
- [A1a](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/results/A1a_20260928T022525Z.md)
- [A1b run 1](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/results/A1b_20260928T031343Z.md),
  [run 2](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/results/A1b_20260928T033612Z.md),
  [run 3](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/results/A1b_20260928T041406Z.md)
- [A2](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/results/A2_20260928T065825Z.md)
- [A3](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/results/A3_20260928T045645Z.md)
- [A5 checkpoint 1](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/results/A5_20260928T073453Z.md),
  [2](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/results/A5_20260928T074919Z.md),
  [3](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/results/A5_20260928T075558Z.md),
  [final](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/results/A5_20260928T082159Z.md)
- [A6](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/results/A6_20260928T085000Z.md)
- [Installed firmware findings](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/docs/esp32_installed_firmware_findings.md)
- [micro-ROS link stability](https://github.com/kihtrak-tns/orin-bringup/blob/2f1306072a4fe828412585b056ec8af1243e3056/notes/microros_link_stability.md)

The evidence advances several Phase A rows beyond the earlier source review.
It remains read-only/isolated bring-up evidence and does not authorize a live
autonomy publisher or promote the car.

## Evidence-based contract matrix

| Interface / safety item | Observed Phase A evidence at the reviewed Orin SHA | Current contract reading | Still unresolved before car promotion |
|---|---|---|---|
| Installed ESP32 message layout | A1a reports 97/97 checks `ALL MATCH`, including raw CDR versus typed values for `Pca9685State`, `VescState`, and `VehicleState`. The battery was unplugged, so VESC controller ID and fresh telemetry were explicitly deferred. Installed image is `cba74e7-dirty`, built 2026-09-05; ELF SHA-256 `fb31999e69da97f8f99459eee75291f84b673eb0df58d0282d5b41805030a17d`. No public source commit exactly matches that dirty image. | The checker-confirmed fields and layouts match the running unpowered interface for A1a's tested values. This is stronger than source reconstruction, but does not identify every uncommitted firmware change or verify powered VESC telemetry. | Preserve the exact installed image provenance; re-check powered fields only in their separately authorized gate. Do not infer a clean source-to-binary match. |
| DriveCommand decode / brake latch | A1b re-run 3 passed 6/6 with battery unplugged and the car on a stand. With `/laksa/brake=false` held during command steps, a 0.1 rad steering request echoed as 0.0981 rad and the PCA command changed 100°→94°; `brake_active` changed false→true on `brake=True`; `command_fresh` became false after silence. The servo itself did not physically move on USB/logic power; a separate human observation with a sustained 0.3 rad request found no linkage motion with the main battery unplugged. | Message decode and the logic/PCA command path are observed. This is not powered steering calibration. The brake latch starts true and re-arms after each micro-ROS session reset; A1b held the separate `/laksa/brake=false` topic continuously to run its test. | Session churn and latch re-arming remain unresolved. Do not infer timeout brake behavior from A1b: `brake_active` was already true before the final silence window. Do not add or assume an automatic latch-release mechanism. |
| A2M12 scan format, rate, and driver | A2 accepted the device default after a stable `/scan` measurement of 12.728 and 12.793 Hz. `sensor_msgs/LaserScan` frame is `laser`, 1,800 beams, approximately −π…π at 0.0035 rad increments, range limits 0.05–16 m, 16 kHz Sensitivity mode; samples had finite returns and about 14% `inf`, no NaN or zero returns in the probes. Driver source pin: `sllidar_ros2@34300099fadfc772965962dec837bf436706188f`. | The observed scan cadence is approximately 12.8 Hz, not the nominal 10 Hz value printed by the driver. Its angle-compensation grid remains sized for 10 Hz, so `inf` bins and nonuniform angular support must retain their semantics during replay. | No measured laser-to-base transform, sensor yaw, or vehicle TF contract is committed. `frame_id=laser` alone does not define placement or steering sign in the vehicle frame. |
| Orin boot services and publishers | A3 passed its reboot gate. The sandbox's source-linked status at the reviewed head records a follow-up reboot after the A5 systemd/udev upgrade: agent and health active, `NRestarts=0`, zero session resets in that check, fresh `/diagnostics` at 1 Hz, and zero publishers on both `/laksa/command` and `/laksa/brake`. | The read-only agent/health boot path works in the recorded check and starts no command publisher. | This does not resolve intermittent micro-ROS session teardown or silent transport stalls over longer windows, and does not choose a sole future command authority. |
| ZED/odometry/TF | A5 reports ZED SDK 5.5.0 and `zed-ros2-wrapper@431dcf4b1ea39caf894ca6ea294437437dbdb034` built and launched for 180 s with no ERROR/FATAL log lines. Reported rates include depth 12.1–12.7 Hz, ZED odometry 26.2–28.0 Hz, and IMU 99.7–100 Hz. While active, wrapper TF includes `map→odom` and `odom→camera_link`. | Camera pipeline and its own temporary TF are observed. ZED odometry is not a measured vehicle-base odometry source. | A6 did not record `/tf` or `/tf_static`; there is no measured `laser→base_link` transform and no agreed single `odom→base` TF authority. |
| A6 bags and motion interpretation | A6 stored `20260928_033352_static` (43.44 s, 4.7 GiB) and `20260928_034706_handcarried` (58.38 s, 4.9 GiB) on the Orin. `/scan` counts/rates were 559/12.86 Hz static and 747/12.81 Hz hand-carried. The latter's ZED odometry extent was 1.83×1.52×0.86 m because the operator carried the car; the static bag stayed near the origin. | The hand-carried bag is useful for offline scan and sensor-pipeline replay, not a vehicle-drive, steering, braking, or autonomous-navigation success. Bags remain on the Orin; a `/scan`-only export is appropriate for transfer. | Do not move the multi-gigabyte image bags for wall-follow replay. Export only `/scan`, preserve serialized message data and bag timestamps, and retain source-bag identity. A6 contains no TF. |
| Speed/eRPM and physical stop | A1b used zero speed only. Findings report a firmware pole-pair mismatch (firmware 7 vs VESC configuration 2), VESC UART timeout 1,000 ms with zero timeout brake current (coast), firmware command timeout 500 ms, and VESC configured ERPM limits ±100,000 while firmware caps at 900. No measured vehicle speed conversion or stopping distance is in A1a/A1b. | The command-unit names do not establish a calibrated metres-per-second to ERPM scale, braking distance, or physical stale-command stop behavior. | Measure speed/eRPM, powered steering direction/endpoints, coast/brake/timeout behavior, loss-of-agent behavior, and physical stopping only under their separately approved gates. |
| Wired stop and final publisher authority | The findings state VESC `kill_sw_mode=0`; A3 found zero command and brake publishers at boot. No A1/A2/A3/A5/A6 result tests an RJ45 stop or establishes a production autonomy authority. | There is no demonstrated independent physical stop path or arbitration owner in this evidence set. | Wired stop behavior and a reviewed single command authority remain blockers. Simulation and scan replay must stay on `/sim/laksa/*` or offline outputs. |
| micro-ROS link stability | The source-linked note records recurring XRCE session teardown/recreation (from ~21 s to ~63 min apart) and one fully silent link interval without teardown; no USB re-enumeration explained it. A6 observed four session resets during the 08:33–08:49Z period under heavy ZED+bag load; the static bag includes a 1.83 s ESP32-topic gap at a reset. | The A1a typesupport issue was fixed by adding `laksa_interfaces` to the Orin agent workspace; the XRCE link instability itself remains open. | Diagnose session churn and silent stalls before any live command publisher or car promotion. |

## Read-only replay disposition

The A6 hand-carried `/scan` topic is suitable as a sensor-only offline input,
but neither its export nor a measured laser transform was available in this
review session. The sandbox therefore provides an exporter that copies only
serialized `/scan` CDR records and their bag timestamps, plus a separate
offline controller preflight using the observed 1,800-beam/12.8 Hz shape. The
preflight is synthetic and is not represented as A6 replay. Real A6 replay
remains **UNVERIFIED** until the small export, transform, and actual request
trace are available.

No output from this path targets `/laksa/command` or `/laksa/brake`. Do not
interpret the hand-carried recording as an autonomous vehicle run.

## Promotion disposition

The Phase A source evidence documents read-only interface checks, LiDAR and
camera sensor operation, service boot, and bag recording. It does not clear the
remaining blockers: micro-ROS session churn/silent stalls, physical stop and
brake behavior, calibrated speed conversion, powered steering calibration,
measured LiDAR transform, and single command authority. No car-promotion gate
is passed by the sandbox simulation or offline replay work.

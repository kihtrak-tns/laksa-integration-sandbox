# LAKSA Architecture Compliance Baseline

**Applies to:** competition target and current Jetson Nano development configuration
**Rules source:** revision 4.2, July 8, 2026
**Status:** approved direction; implementation evidence incomplete

## Current architecture

| Layer | Current responsibility | Competition constraint |
|---|---|---|
| ZED 2i and RPLIDAR A2-M12 | Perception and localization inputs | Must remain within size, weight, power, budget, and onboard-only operation rules. |
| Jetson Nano | Development compute for localization, mapping, path logic, visual start, lap count, and vehicle-level requests | Must not be treated as safety authority; final competition compute remains unfrozen. |
| Teensy 4.1 | Safety state, request validation, freshness, limits, neutralization, wired E-stop handling, and actuator authority | Must fail safe independently of Jetson/ROS/wireless systems. |
| ESP32 | Temporary demo adapter or nonessential bench/telemetry device | Must not provide an off-track competition control path. |
| Pololu/vehicle adapter/ESC or VESC | Routes and applies steering/propulsion outputs | Exact competition electrical design and calibration remain gated. |

## Control boundary

```text
onboard sensors -> Jetson autonomy -> vehicle-level motion request
                                      |
                                      v
course RJ45 stop -----------------> Teensy safety authority -> actuator path
```

Competition mode must reject RC, Xbox, Wi-Fi dashboard, Bluetooth, and other off-track control commands. A separate bench mode may permit them, but the transition and lockout must be explicit, testable, logged, and part of the pre-run checklist.

## Allowed now

- Repository and Rules Guardian setup.
- ZED/RPLIDAR independent bring-up.
- Recorded-data ingestion, transforms, health monitoring, and logging.
- Localization and path-generation prototypes.
- Visual-start detector interface with configurable parameters and synthetic/provisional tests.
- Lap-counter interfaces and simulation tests.
- Motion-request generation ending at `MockVehicleControl`.
- Teensy unit tests that do not connect unknown-voltage vehicle signals or energize actuators.

## Blocked until evidence exists

| Gate | Rule basis | Minimum clearing evidence |
|---|---|---|
| Live competition steering/throttle | 1.1; 1.2.9; 2.4; 2.5 | Reviewed electrical interface, wheels-up tests, fresh-command timeout, neutralization, state-machine logs, and competition-mode lockout. |
| Course RJ45 connection | 1.2.2.1–1.2.2.4 | Organizer electrical clarification, schematic, safe biasing/isolation decision, open-wire/disconnect tests, and stop-latency results. |
| Final visual-start behavior | 2.5.1; 3.4 | Final 2026 visual specification and representative validation set. |
| On-course teach-and-repeat using remote drive | 2.4; 4.1.1 | Written organizer answer to `CLAR-007`. |
| Competition release | all applicable rules | Completed release checklist and a Rules Guardian review against a tagged public commit. |

## Legacy official README warning

The official repository's current README was prepared before the rulebook and current hardware selections were known. Its RPLIDAR C1, dual JGB37 motors, Cytron MDD10A, MG996R, 3S battery, optional camera, and active remote-override assumptions are obsolete. Retain it as history until replaced through review; do not implement from it.

## Initial Rules Guardian disposition

**Overall: `ALLOW WITH CONDITIONS` for sandbox and mock/sensor-only work; `BLOCK` for live competition actuation.**

The selected hardware is not prohibited, but the current robot cannot be called competition-compliant until the RJ45 stop path, competition-mode remote-command rejection, autonomous start/stop, lap counting, physical measurements, battery plan, and required evidence are completed.

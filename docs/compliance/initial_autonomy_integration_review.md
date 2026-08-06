# Rules Guardian Review — Initial LAKSA Autonomy Integration

**Review date:** August 6, 2026
**Rules source:** DIY Robot Challenge Rules 2026, revision 4.2
**Reviewed scope:** private sandbox setup; Jetson Nano + ZED 2i + RPLIDAR A2-M12 sensor/autonomy foundation; Teensy 4.1 as intended safety authority; no live actuation
**Overall decision:** `ALLOW WITH CONDITIONS` for sandbox, sensor-only, recorded-data, and mock-control work. `BLOCK` live competition steering/throttle.

| Rule ID | Outcome | Finding | Evidence | Disposition |
|---|---|---|---|---|
| 0.1.1 | `NON-COMPLIANT` | No proprietary-IP audit is recorded yet. | Audit required before public promotion. | `ALLOW` private scaffolding; `BLOCK` official competition release. |
| 0.1.2 | `COMPLIANT` | Official LAKSA is public and the sandbox plan preserves promotion into it. The private sandbox alone would not satisfy the rule. | `Project-LAKSA/Project_LAKSA`; documented clean-promotion workflow. | `ALLOW`. |
| 0.2.4–0.2.4.1 | `NON-COMPLIANT` | The required August 14 L-path demonstration has not yet been evidenced. | Required video and synchronized logs absent. | `ALLOW` implementation; `BLOCK` milestone-complete claim. |
| 1.1–1.1.2 | `NOT APPLICABLE` | Current approved scope cannot command physical actuation. | `MockVehicleControl` boundary. | `ALLOW`; re-review before hardware output. |
| 1.2–1.2.2.4 | `NON-COMPLIANT` | Mandatory RJ45 course stop interface is not designed/verified. | Schematic, electrical limits, and fault-injection evidence absent. | `BLOCK` competition/live actuation. |
| 1.2.9 | `NON-COMPLIANT` | Propulsion cessation and bounded-steering behavior lack vehicle evidence. | Stop latency/distance and wheels-up tests absent. | `BLOCK` competition/live actuation. |
| 2.2.1 | `NOT APPLICABLE` | Repository/sensor-mock work does not change physical envelope. | No new mounts in scope. | `ALLOW`; physical integration remains open. |
| 2.2.2 | `NOT APPLICABLE` | Repository/sensor-mock work does not change vehicle weight. | No physical configuration in scope. | `ALLOW`; race-ready weighing remains open. |
| 2.4–2.4.1 | `NEEDS ORGANIZER CLARIFICATION` | Competition design rejects remote commands, but electrical radio disablement and outbound telemetry remain ambiguous. | `CLAR-003` open. | `ALLOW` offline/bench work; `BLOCK` final radio configuration. |
| 2.5.1; 3.4 | `NEEDS ORGANIZER CLARIFICATION` | Final 2026 signal/background/state/timing are unknown. | Prior-year drawing only; `CLAR-004` open. | `ALLOW` configurable interface and synthetic tests; `BLOCK` frozen thresholds. |
| 2.5.2 | `NON-COMPLIANT` | Autonomous lap counting and target-lap stop are not implemented or verified. | Three-lap/two-lap evidence absent. | `ALLOW` interface/unit-test work; `BLOCK` competition release. |
| 2.7 | `NOT APPLICABLE` | No battery choice or physical runtime claim is changed by this scope. | None required for mock-only work. | `ALLOW`; three-heat test remains open. |
| 4.1.1; 2.4 | `NEEDS ORGANIZER CLARIFICATION` | Manual practice-heat course teaching is not explicitly allowed. | `CLAR-007` open. | `BLOCK` on-course manual teach-and-repeat as competition baseline. |
| 5.2–5.2.1 | `NON-COMPLIANT` | A same-day SharePoint revision check is not recorded in the sandbox package. | Revision 4.2 checksum is preserved, but archive currency needs team verification. | `ALLOW` scaffolding; recheck before every formal gate. |

## Conditions on allowed work

1. All generated motion requests terminate at `MockVehicleControl`.
2. No unknown receiver/ESC/servo voltage is connected to Teensy GPIO.
3. The original rulebook and prior-year signal artwork are not published without permission.
4. The visual detector remains configurable and treats unknown/stale input as do-not-start.
5. Competition communications are designed around rejection of off-track commands, pending `CLAR-003`.
6. Every new PR includes a Rules Guardian table and evidence links.

## Immediate next work sequence

### G1 — Sandbox and Guardian foundation

- Create/seed `kihtrak-tns/laksa-integration-sandbox` from the current official Git history.
- Add the Rules Guardian on `codex/rules-guardian-v1`.
- Pass deterministic validation and open a draft sandbox PR.
- Do not modify official LAKSA.

### G2 — Reconcile existing development history

The official repository does not contain the previously reported Teensy/autonomy commits. In the local personal worktrees, inspect and preserve:

- the claimed A0 autonomy commit `4b743f4`;
- Teensy T1–T3 code and evidence;
- the semantic contract;
- all dirty/uncommitted user files.

Do not assume those SHAs belong to the current official ancestry. Produce a commit/tree comparison first, then import only reviewed changes into isolated sandbox branches.

### A1 — Sensor and mock-control milestone

- Record Jetson Nano JetPack/L4T/Ubuntu/ROS compatibility.
- Validate ZED 2i and RPLIDAR A2-M12 independently.
- Define measured transforms and health/status interfaces.
- Record synchronized sensor/TF/odometry/system-load data.
- Implement or recover the vehicle-control abstraction and `MockVehicleControl` tests.
- Generate a simple L-path request sequence without physical output.

### T4 — Separate safety/electrical milestone

- Complete the vehicle electrical interface audit before wiring.
- Resolve receiver signal-level compatibility; do not directly connect an unknown potentially 6 V PWM signal to Teensy 4.1.
- Define the course RJ45 stop input architecture only after `CLAR-009` or conservative isolation requirements are established.
- Validate state-machine timeout, neutralization, and output limits independently of Jetson.

### August 14 demonstration gate

The rule requires actual vehicle motion. After A1 and T4 evidence clears the live-actuation block, progress through actuator-disabled link, wheels-up steering, wheels-up low throttle, E-stop/heartbeat-loss tests, then a low-speed L-path ground run with a spotter and physical stop capability. Do not bypass those gates to meet the date.

## Scope not reviewed

- final Teensy pinout and voltage-interface components;
- final VESC/ESC and steering-servo implementation;
- mechanical sensor mounts and measured envelope;
- battery/power distribution and runtime;
- final 2026 visual-indicator specification;
- course layout/CAD and obstacle strategy;
- final competition compute selection.

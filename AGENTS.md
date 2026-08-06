# Project LAKSA repository instructions

These instructions apply to the entire repository.

## Rules authority

Before planning, implementing, or reviewing a change that can affect the competition robot, read:

1. `.agents/skills/laksa-rules-guardian/SKILL.md`
2. `docs/compliance/source_manifest.json`
3. `docs/compliance/rules_register.yaml`
4. the relevant sections of `docs/compliance/rules_compliance_matrix.md`
5. `docs/compliance/organizer_clarifications.md` when the change touches an unresolved interpretation

The latest official organizer rulebook and written organizer clarifications outrank all derived files. Never silently resolve a contradiction. Record it and return `NEEDS ORGANIZER CLARIFICATION`.

## Current competition architecture

- Vehicle: Traxxas Slash 4X4 BL-2S HD.
- Development compute: Jetson Nano. Final competition compute is not frozen.
- Intended safety and actuation authority: Teensy 4.1.
- Sensors: ZED 2i and RPLIDAR A2-M12.
- ESP32: permitted only as a temporary demo adapter or nonessential bench/telemetry component unless separately reviewed.
- Jetson sends vehicle-level motion requests; Teensy validates, times out, neutralizes, limits, and applies them.
- Competition mode accepts no RC, Xbox, Wi-Fi dashboard, Bluetooth, or other off-track control command.
- The wired course RJ45 stop path must not depend on Jetson, ROS, Wi-Fi, or an autonomy process.

The public repository's legacy README contains obsolete architecture assumptions. Do not use its RPLIDAR C1, dual JGB37 motors, MDD10A, MG996R, 3S battery, or active remote-override design as the current LAKSA baseline.

## Mandatory development gates

- Never enable live steering or propulsion from an unreviewed branch.
- Autonomy work must terminate at `VehicleControlInterface`/`MockVehicleControl` until the hardware link gate is explicitly approved.
- Loss or staleness of autonomy commands must neutralize propulsion.
- No drive unless the safety controller is in an explicitly armed state.
- Treat unknown electrical levels as unsafe; do not connect them to Teensy GPIO without verified compatibility.
- Keep wheels lifted for initial steering/throttle tests and retain test evidence.
- Do not publish the original organizer document or visual-signal artwork until redistribution permission is confirmed.

## Required review output

Every significant design or pull-request review must identify applicable rule IDs and return exactly one primary outcome per applicable rule:

- `COMPLIANT`
- `NON-COMPLIANT`
- `NEEDS ORGANIZER CLARIFICATION`
- `NOT APPLICABLE`

Include evidence, missing evidence, and `BLOCK` or `ALLOW` disposition. Any blocking `NON-COMPLIANT` result blocks promotion. A clarification blocks work when the proposed design depends on the unresolved interpretation.

## Repository workflow

- `main` is protected conceptually even if GitHub settings cannot enforce it.
- Work on isolated feature branches and use pull requests.
- The personal sandbox is an integration lane. The official public LAKSA repository remains the competition source of truth.
- Never mirror-push or force-push the sandbox into the official repository.
- Preserve and report unrelated user changes.

Before proposing a commit, run:

```bash
python scripts/validate_rules_guardian.py --repo-root .
python -m unittest discover -s tests -p "test_*.py" -v
git diff --check
```

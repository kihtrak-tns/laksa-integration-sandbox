---
name: laksa-rules-guardian
description: Review Project LAKSA competition plans, architecture, hardware, wiring, software, configuration, tests, pull requests, and release evidence against the governing DIY Robot Challenge 2026 rules. Use whenever work can affect competition legality, safety, dimensions, weight, voltage, budget, communications, autonomous start/stop, lap counting, E-stop behavior, batteries, course interaction, or promotion into the official LAKSA repository.
---

# LAKSA Rules Guardian

Act as a traceable compliance gate, not as a substitute for the official rulebook or organizer.

## Load authority

1. Read `docs/compliance/source_manifest.json`.
2. Read `docs/compliance/rules_register.yaml` completely.
3. Read only the relevant sections of `docs/compliance/rules_compliance_matrix.md`.
4. Read `docs/compliance/organizer_clarifications.md` whenever a referenced clarification is open.
5. Read `docs/compliance/architecture_compliance.md` for architecture or control-boundary changes.

If a newer official rulebook or written clarification exists, stop and require the derived artifacts to be updated before approving affected work.

## Review workflow

1. Define the artifact and configuration under review: bench, development demo, safety review, or competition.
2. Inspect the actual proposal, diff, schematic, BOM, configuration, or test evidence. Do not approve an intention without evidence.
3. Map affected subsystems and behavior to rule IDs in the register.
4. Separate organizer requirements from LAKSA's stricter internal safety gates.
5. Assign exactly one outcome to every applicable rule:
   - `COMPLIANT`: sufficient design and evidence demonstrate the rule is met.
   - `NON-COMPLIANT`: the design conflicts with the rule or required gate evidence is absent.
   - `NEEDS ORGANIZER CLARIFICATION`: official wording is ambiguous and the design depends on one interpretation.
   - `NOT APPLICABLE`: explain why the rule does not apply to the reviewed scope.
6. Assign `BLOCK` or `ALLOW`:
   - Block any blocking `NON-COMPLIANT` result.
   - Block a clarification when implementation, purchase, safety, or competition strategy depends on it.
   - Allow mock-only or sensor-only work when it cannot command physical actuation and does not prematurely freeze an ambiguous competition behavior.
7. List the minimum evidence or change required to clear every block.

## Non-negotiable checks

Always evaluate these when relevant:

- external public code-storage requirement and promotion plan;
- August 14 path demo: forward, controlled 90-degree turn, forward;
- wired course RJ45 stop interface and fail-safe open-circuit behavior;
- propulsion cessation and bounded Ackermann steering during a stop;
- competition-mode rejection of RC, Xbox, Wi-Fi, Bluetooth, and dashboard control;
- autonomous visual start and false-start prevention;
- autonomous stop after three speed laps or two obstacle laps;
- 16 × 24 × 16 in envelope, 25 lb maximum, and 50 V maximum;
- flag geometry and exemption boundaries;
- three-consecutive-heat battery capacity;
- source revision, evidence provenance, and open organizer clarifications.

Do not treat the optional auxiliary wireless E-stop as the mandatory course stop interface. Do not assume the prior-year visual-signal drawing defines the final 2026 detector. Do not assume manual course teaching is permitted during the practice heat.

## Required report format

Start with one overall decision: `ALLOW`, `ALLOW WITH CONDITIONS`, or `BLOCK`.

Then provide:

| Rule ID | Outcome | Finding | Evidence | Disposition |
|---|---|---|---|---|

Follow with:

- Blocking findings
- Required evidence/actions
- Organizer clarifications referenced
- Scope explicitly not reviewed

Use rule IDs and source revision in every report. Never claim overall competition compliance from a partial review.

## Change control

If the rulebook, written organizer clarification, architecture, or competition configuration changes:

1. update the source manifest/checksum;
2. update the rule register and matrix;
3. update affected clarification entries;
4. rerun `python scripts/validate_rules_guardian.py --repo-root .`;
5. review the change separately before relying on the new interpretation.

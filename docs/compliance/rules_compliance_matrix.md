# Project LAKSA — 2026 Competition Rules Compliance Audit

**Status:** Draft for team approval and organizer clarification
**Rules source:** *DIY Robot Challenge Rules 2026.docx*
**Source revision:** 4.2, July 8, 2026
**Audit date:** August 6, 2026
**Source SHA-256:** `9c99a80df3777ad33750955dd4d5d1cc3c4deadc8ea8aa0f389aa520421c754b`

## 1. Executive conclusion

The current LAKSA hardware concept—Traxxas Slash 4X4 BL-2S HD, Jetson Nano for development, Teensy 4.1 as the intended safety/actuation authority, ZED 2i, and RPLIDAR A2-M12—is not prohibited by revision 4.2. However, it is not yet competition-compliant because several mandatory functions and measurements remain unimplemented or unverified.

The five most important consequences are:

1. **The path-following demonstration is due August 14, 2026.** It must show forward motion, a controlled 90-degree turn, and forward motion afterward.
2. **Competition control must be fully autonomous.** Xbox control, the RC transmitter/receiver path, and dashboard commands must not control the robot during a run. The course E-stop and RTK GNSS are the only explicit exceptions.
3. **A wired course E-stop interface is mandatory.** LAKSA must provide an RJ45 socket that treats continuity between the pin groups as RUN and isolation as STOP. This must reach the Teensy safety path without depending on the Jetson, ROS, Wi-Fi, or the autonomy process.
4. **The robot must recognize the course's visual start signal and stop itself after the required lap count.** A pre-taught path alone does not satisfy these two requirements.
5. **A manually driven teach run on the competition course is not clearly authorized.** Off-course development and replay are fine, but competition-course teach-and-repeat must not become the primary competition strategy until organizers clarify whether remote driving is permitted during the practice heat.

No physical competition integration should be declared complete until the E-stop circuit, competition-mode control lockout, dimensions, weight, voltage, batteries, flag, visual start, and lap-stop evidence are all closed.

## 2. Authority and numbering

This audit treats the uploaded revision 4.2 document as the governing source. The rulebook's top-level competition-rule numbering begins at **0**, as confirmed by its revision notes and internal cross-references. Therefore this audit uses:

- 0 — General Rules
- 1 — Safety Rules
- 2 — Robot Rules
- 3 — Course Rules
- 4 — Race Rules
- 5 — Knowledge Sharing & Engagement

The original rulebook remains authoritative. This audit paraphrases it for engineering use and does not replace it. SharePoint-hosted organizer documents should be rechecked for revisions before every formal review because Rule 5.2 says organizer documents are archived there and other copies have no guaranteed update frequency.

## 3. Status definitions

| Status | Meaning |
|---|---|
| `ALIGNED` | The current architecture is compatible with the rule, but normal implementation evidence may still be required. |
| `OPEN-DESIGN` | A required function or process has not been fully designed or implemented. |
| `OPEN-EVIDENCE` | The likely design is acceptable, but measurement, test, or documentation is missing. |
| `CLARIFY` | Organizer interpretation is needed before relying on the design choice. |
| `CONFLICT` | A current behavior would violate the rule if used during competition. |
| `PROCESS` | Primarily a team, event, or documentation obligation rather than a vehicle design item. |
| `OPTIONAL` | Explicitly optional under the rulebook. |

## 4. Architecture decisions forced by the rules

### 4.1 Competition control boundary

The Teensy remains the safety and actuation authority. During a competition run it must accept motion requests only from the onboard Jetson autonomy process. It must reject or ignore RC receiver, Xbox, Wi-Fi dashboard, Bluetooth, and other off-track control inputs.

Manual control may remain available as a physically or logically segregated **bench/development mode**, but the competition-mode transition must be explicit, testable, and included in the pre-run checklist. Merely promising not to touch the transmitter is weaker than disabling the command path.

### 4.2 Required E-stop path

The mandatory course interface is a dry-contact-style RJ45 connection:

- Pins 1–4 form one common group.
- Pins 5–8 form the other common group.
- RUN: the two groups are electrically connected.
- STOP: the two groups are isolated.

The robot must interpret an open circuit, disconnected cable, broken conductor, MCU reset, invalid input, or uncertain state as STOP. The final electrical design must establish safe biasing, voltage compatibility, connector pin use, debounce, diagnostics, and fault injection. The current rulebook does not specify the electrical voltage/current limits of the organizer interface; this must be confirmed before finalizing the interface electronics.

The optional team-provided wireless E-stop is not required by Rule 1.2.3. LAKSA should initially use the course-provided activator and mandatory wired robot interface unless an auxiliary system delivers a clear operational advantage.

### 4.3 E-stop behavior and resumption

On E-stop assertion, propulsion must cease within the required response time. Ackermann steering may remain active only to prevent a collision until the robot stops. The safest LAKSA policy is:

1. Neutralize propulsion immediately.
2. Permit only bounded collision-avoidance steering while vehicle speed is nonzero.
3. Preserve the onboard mission state needed for a safe restart.
4. On E-stop clear, require stable RUN continuity, healthy onboard sensors, fresh Jetson commands, a valid competition mission, and no independent Teensy fault before propulsion resumes.
5. Never require an off-track RC command to resume.

The existing concept of a permanently latched E-stop requiring manual recovery is acceptable for bench safety but would force a manual-start penalty after a course intervention. Competition firmware should support a separately validated safe auto-resume policy.

### 4.4 Autonomy functions that are now mandatory

The onboard stack needs explicit state-machine support for:

- visual start-signal detection;
- false-start protection;
- autonomous mission start;
- lap counting for three speed-course laps and two obstacle-course laps;
- autonomous stop after the target lap count;
- course E-stop pause and safe resume;
- ten-minute heat termination behavior;
- onboard-only logging and diagnostics;
- zero dependence on remote commands or network availability.

### 4.5 Sensor and compute interpretation

Revision 4.2 does not prohibit ZED 2i, RPLIDAR A2-M12, Jetson Nano, Teensy 4.1, ESP32, VESC, or the Traxxas chassis. Sensor legality is therefore `ALIGNED`, subject to the overall size, weight, voltage, safety, budget, and no-remote-control rules.

The ESP32 may be retained for nonessential telemetry or bench tooling, but competition operation must not depend on it unless its exact function is brought inside the compliance boundary. A Wi-Fi dashboard must not arm, steer, throttle, resume, or otherwise control the robot during a heat.

## 5. Rule-to-design compliance matrix

### 5.1 General rules

| Rule | Engineering interpretation | LAKSA status | Required evidence/action |
|---|---|---|---|
| 0.1.1 | No Caterpillar proprietary IP may be used on the vehicle. | `OPEN-EVIDENCE` | Perform a source/data/dependency audit. Do not use internal vehicle code, confidential datasets, internal algorithms, or proprietary drawings. |
| 0.1.2 | Code storage must use an external repository such as public GitHub or public GitLab, not internal enterprise/gitgis services. | `ALIGNED` | Use the public `Project-LAKSA/Project_LAKSA` repository. Add branch protection and public-safe documentation practices. |
| 0.1.3–0.1.5 | Novelty and possible future Cat use have IP-process implications. | `PROCESS` | Avoid unpublished proprietary inventions; request organizer/IP guidance if a component appears novel. |
| 0.2.1 | Team must include at least two Cat Technology or Cat Digital employees. | `PROCESS` | Captain records eligible team roster. |
| 0.2.2–0.2.3 | Design review and Cat-funded-parts deadline obligations. | `PROCESS` | Preserve design-review and parts-list evidence if Cat funding was used. |
| 0.2.4–0.2.4.1 | Path-following demo due August 14; forward, controlled 90-degree turn, then forward. | `OPEN-DESIGN` | Treat as immediate milestone. Use onboard autonomy, low speed, a simple L-shaped path, and a safe actuator controller. Retain video and logs. |
| 0.2.5–0.2.5.3 | Mandatory safety review; demonstrate stop assertion, clearing, and heartbeat timeout; in-person representatives required. | `CLARIFY` | Confirm September 23 vs September 25 and define which heartbeat is being tested. Prepare repeatable E-stop fault-injection evidence. |
| 0.3.1–0.3.2 | US customary dimensions govern; course dimensions may vary ±1 inch unless stated otherwise. | `ALIGNED` | Design margins against the worst credible course geometry, not the nominal centerline only. |

### 5.2 Safety rules

| Rule | Engineering interpretation | LAKSA status | Required evidence/action |
|---|---|---|---|
| 1.1–1.1.2 | Robot must not endanger people or other robots; staff may stop and reinspect it. | `OPEN-EVIDENCE` | Maintain hazard analysis, guards, secured batteries, strain relief, thermal protection, conservative speed limits, and a pre-run inspection. |
| 1.2–1.2.2.4 | Mandatory course E-stop connection through an RJ45 socket using the specified closed=RUN/open=STOP contact behavior. | `OPEN-DESIGN` | Design and bench-test the Teensy-side interface. Provide wiring drawing, continuity test, open-wire fault test, and disconnect test. |
| 1.2.3 | Auxiliary team E-stop is optional. | `OPTIONAL` | Defer unless the course system is insufficient for team testing or operations. |
| 1.2.4–1.2.7.2 | If an auxiliary E-stop is used, it must be wireless, noninterfering, fail-safe, and stop within one second on signal loss or stop request; 300 ft range is recommended. | `OPTIONAL` | Do not claim compliance until range, interference, loss-of-link, and response-time tests exist. |
| 1.2.8 | Event staff and teams may use activation devices around the course. | `PROCESS` | Train designated operator and document stop-call protocol. |
| 1.2.9 | E-stop must cease propulsion; limited Ackermann steering may continue only to prevent collision until stopped. | `OPEN-DESIGN` | Implement propulsion neutralization independently of Jetson. Measure stop latency and distance at approved test speeds. Bound post-stop steering to neutral. |
| 1.2.10 | Automatic resume after E-stop clear is allowed when safe. | `OPEN-DESIGN` | Implement guarded auto-resume as a competition policy; retain a no-resume fault state for independent failures. |
| 1.3 | Humans enter only after all robots are E-stopped and stopped. | `PROCESS` | Add this to operating procedure and intervention training. |

### 5.3 Robot rules

| Rule | Engineering interpretation | LAKSA status | Required evidence/action |
|---|---|---|---|
| 2.1.1–2.1.3 | Cat funding is capped at $1,000; a provided perception sensor is excluded; personal spending above the cap is allowed. | `OPEN-EVIDENCE` | Keep a component ledger with payer/source. Confirm whether the ZED 2i is the organizer-provided exempt sensor. |
| 2.2.1 | Robot envelope must never exceed 16 in W × 24 in L × 16 in H. | `OPEN-EVIDENCE` | Measure the complete configured vehicle at steering extremes and with all sensors, guards, connectors, cables, and mounts. Record photos and a signed measurement sheet. |
| 2.2.2 | Robot must not exceed 25 lb. | `OPEN-EVIDENCE` | Weigh the race-ready robot with battery, compute, sensors, E-stop hardware, mounts, and cables. |
| 2.3 | Onboard electrical systems must never exceed 50 V. | `ALIGNED` | Document maximum charged battery voltage and every power rail. Use fuse/protection evidence. |
| 2.4–2.4.1 | No communication with off-track remote-control-like systems while competing; E-stop and RTK GNSS are exempt. | `CONFLICT` for current manual/dashboard paths if active | Create a competition mode that rejects RC, Xbox, Bluetooth, Wi-Fi, and dashboard control. Keep transmitter/controller off during runs. Ask whether outbound-only telemetry is permitted before enabling it. |
| 2.5–2.5.1 | Robot must start and stop autonomously; start is based on a visual course signal. | `OPEN-DESIGN` | Obtain start-indicator specification. Add detection confidence, temporal qualification, false-start tests, and state-machine integration. |
| 2.5.2 | Robot must stop after the specified lap count. | `OPEN-DESIGN` | Implement and validate robust lap counting: three speed laps and two obstacle laps. Add timeout and duplicate-crossing rejection. |
| 2.6–2.6.10 | Mandatory team flag; top 24–26 in above ground; mount point ≤8 in; flag itself is exempt from robot envelope and weight. | `OPEN-DESIGN` | Add low flag mount, flexible wire clearance, and pre-inspection measurements. Do not place the mounting point on a high sensor mast. |
| 2.7 | Batteries must support at least three consecutive heats; charging may be limited. | `OPEN-EVIDENCE` | Produce a full-system runtime test and bring a documented three-heat energy plan for traction and compute supplies. |

### 5.4 Course rules

| Rule | Engineering interpretation | LAKSA status | Required evidence/action |
|---|---|---|---|
| 3.1–3.3 | Separate speed and obstacle courses; layouts/intersection instructions are provided; minimum track width is 20 in. | `OPEN-EVIDENCE` | Obtain the current course-layout PDF and obstacle CAD. Validate the full vehicle footprint and turning envelope with construction tolerance. |
| 3.4 | Both courses use a vision-based starting indicator. | `OPEN-DESIGN` | Assign ZED start-detector responsibility and validate against the actual indicator. |
| 3.4.1 | Manual start is allowed with a five-second penalty as an exception to autonomous/no-remote rules. | `ALIGNED` as fallback | Define a rule-compliant manual trigger method only after organizer clarification; do not make it the baseline. |
| 3.5–3.5.4 | Teams may request stop/retrieval only through the timekeeper, E-stop operator, and race director process. | `PROCESS` | Add intervention callouts and roles to the runbook. |
| 3.5.5–3.5.5.2 | After the field clears and E-stop is released, robot should resume without remote control; manual restart incurs the 3.4.1 penalty. | `OPEN-DESIGN` | Preserve mission/lap state through E-stop and implement guarded onboard resume. |
| 3.5.6–3.5.6.1 | Team may end early; removing the robot during intervention requires a new run. | `PROCESS` | Include strategy decision and reset procedure in runbook. |
| 3.6.1–3.6.2 | Speed course requires three consecutive timed laps; intervention replacement cannot exceed prior forward progress. | `OPEN-DESIGN` | Validate lap count and recovery behavior; do not assume the robot may be placed ahead. |
| 3.7.1–3.7.3.3 | Obstacle course requires two laps; intervention/skip options and escalating penalties apply. | `OPEN-DESIGN` | Build per-obstacle completion detection and a strategy model comparing retry versus skip. Revalidate nominal penalty when organizers finalize it. |
| 3.8–3.8.7 | Team fiducials are optional and constrained in size, height, placement, attachment, setup, and removal. | `OPTIONAL` | Do not depend on fiducials until course setup time and permitted locations are evaluated. If used, prepare a placement plan and damage-free attachment method. |

### 5.5 Race and engagement rules

| Rule | Engineering interpretation | LAKSA status | Required evidence/action |
|---|---|---|---|
| 4.1–4.1.3 | One practice heat; 2–4 scored heats per course; best time counts. | `PROCESS` | Predefine practice-heat calibration checklist and configuration-freeze procedure. |
| 4.2–4.2.4 | Each heat is ten minutes; multiple runs may occur; E-stop is asserted at heat end. | `OPEN-EVIDENCE` | Verify thermal, battery, logging, and restart behavior across a complete ten-minute heat and repeated runs. |
| 4.3–4.3.3 | Team designates a continuously attentive E-stop operator who acts immediately. | `PROCESS` | Assign primary/backup operators and rehearse commands. |
| 4.4 | Vehicle remains on track until motion ceases and the race director declares access safe. | `PROCESS` | Include in retrieval runbook. |
| 5.1–5.1.2 | Organizer Q&A uses Cat Robotics Stack Overflow with the DIY-Robot-Challenge tag. | `PROCESS` | Submit ambiguities there so answers are visible and traceable. |
| 5.2–5.2.1 | SharePoint is the official archive; external copies may be stale. | `PROCESS` | Record rule revision/checksum in every release and recheck SharePoint before demo, safety review, and competition. |

## 6. Organizer clarification register

These questions should be submitted using the official DIY-Robot-Challenge Q&A channel. The requested answer should cite the rule revision or become a written organizer clarification.

| Priority | Rules | Question to submit | Why it matters |
|---|---|---|---|
| P0 | Timeline; 0.2.5 | The introductory timeline lists September 23 for the safety review, while Rule 0.2.5 lists September 25 and 0.2.5.3 says the week of September 25. Which date and site-specific time are binding? | Scheduling and travel. |
| P0 | 0.2.5.2; 1.2 | What exact heartbeat must be demonstrated during the safety review? Is it the optional auxiliary wireless E-stop heartbeat, an onboard compute-to-safety-controller watchdog, or another course-interface heartbeat? | The mandatory wired course interface is described only as continuity/open circuit, while the auxiliary wireless interface is optional. |
| P0 | 2.4; 3.4.1 | During a heat, must RC receivers, Wi-Fi, and Bluetooth radios be electrically disabled, or is it sufficient that the robot rejects all non-E-stop control commands? Is outbound-only telemetry allowed? | Determines competition-mode hardware and software lockout. |
| P0 | 2.5.1; 3.4 | Provide the visual start indicator specification: appearance, location, size, states, transition timing, illumination, and whether a sample/test artifact will be available. | Required autonomous-start perception cannot be designed reliably without it. |
| P1 | 3.4.1 | What forms of alternative manual trigger are permitted for the five-second-penalty start? | Defines a compliant fallback without accidentally enabling remote control. |
| P1 | 3.5.5; 1.2.10 | After E-stop clear, is a timed guarded auto-resume expected, or may the robot remain stopped and accept the manual-start penalty? Are there minimum delay or indication requirements? | Determines Teensy state-machine policy. |
| P1 | 2.4; 4.1.1 | During the unscored practice heat, may a team manually drive the robot to collect a map or taught path, or must all robot motion on-course be autonomous? | Teach-and-repeat legality. Until answered, do not make manual course teaching the competition baseline. |
| P1 | 2.1.2 | Is the ZED 2i the provided perception sensor that is excluded from the Cat-funded $1,000 budget, and is the exemption limited to one specific supplied unit? | Budget ledger. |
| P1 | 1.2.2.1–1.2.2.4 | What voltage/current may the robot apply to the course RJ45 contact interface, are all eight conductors present end-to-end, and are there isolation/polarity requirements? | Safe electrical-interface design. |
| P1 | 2.2.1; 2.6.10 | Confirm that only the issued flag/wire is exempt from the 16-inch height limit, while the mount, mast, sensors, and other hardware remain inside the envelope. | Mechanical packaging. |
| P2 | 3.2 | When will the final course-layout and intersection instructions be frozen, and can they change after the practice heat begins? | Map and route planning. |
| P2 | 3.7.3.1 | Confirm the final nominal obstacle penalty and the promised communication date. | Retry/skip strategy. |

## 7. Immediate milestone plan: August 14 path-following demo

The path-following deadline is eight days after this audit. The lowest-risk demonstration scope is deliberately narrow:

> From rest, the Slash autonomously follows a simple L-shaped reference consisting of a straight segment, one controlled 90-degree turn, and a second straight segment, then commands neutral and remains stopped.

### Required demonstration properties

- Onboard start command for the demo; no continuous remote steering/throttle.
- Low, capped speed and bounded steering.
- Teensy preferred as the final controller, but the already-proven ESP32/VESC path may serve as a temporary demo adapter if Teensy competition I/O is not electrically ready. This does not change Teensy as the competition target.
- Jetson Nano produces motion requests through the existing abstract vehicle-control interface.
- Pose/path tracking should use the simplest sensor pipeline proven stable on the Nano. Do not force simultaneous ZED depth, ZED odometry, RPLIDAR SLAM, mapping, recording, and control unless measured headroom supports it.
- A physical E-stop/spotter setup for development testing, even if the final course RJ45 interface is not yet available.
- Video plus time-synchronized logs of pose, reference path, steering request, propulsion request, applied outputs, controller state, command freshness, and faults.

### Decision gate for the demo controller

Use this order of preference:

1. Teensy, only if steering/throttle output, neutralization, timeout, and electrical interfaces pass wheels-up testing in time.
2. Existing ESP32/VESC actuation adapter, if it is already stable and can enforce neutral on stale Jetson commands.
3. Do not rush unverified Teensy receiver-level wiring merely to satisfy the demo. RC monitoring and competition manual-mode wiring are not required for an autonomous L-path demonstration and can remain isolated.

## 8. Compliance evidence package

The team should retain the following evidence against a tagged competition release:

- exact rulebook revision and SHA-256;
- public repository commit/tag;
- bill of materials with funding source;
- vehicle width/length/height and weight record;
- maximum-voltage and power-distribution record;
- E-stop schematic and RJ45 pinout;
- E-stop assertion, cable-disconnect, clear, and heartbeat-timeout test logs;
- stop latency and stop-distance results at approved speeds;
- competition-mode remote-command rejection test;
- visual-start validation set and false-start results;
- lap-count and autonomous-stop tests;
- three-consecutive-heat battery/runtime test;
- ten-minute thermal/load test;
- flag mount measurements;
- path-following demo video/logs;
- safety-review checklist and signoff;
- organizer clarifications with dates and links.

## 9. Rules Guardian implementation gate

This audit should be reviewed by the LAKSA team before it is converted into repository enforcement. After approval and after the project repository is attached, the next implementation package should contain:

```text
docs/compliance/
├── rules_compliance_matrix.md
├── rules_register.yaml
├── organizer_clarifications.md
├── architecture_compliance.md
└── competition_release_checklist.md

.agents/skills/laksa-rules-guardian/
└── SKILL.md

.github/
├── pull_request_template.md
└── workflows/rules-compliance.yml
```

The public repository should contain the derived rule register and citations, not automatically publish the organizer's original Word document or internal SharePoint links. Confirm document redistribution permission first.

Every design or pull-request review should return exactly one primary outcome per applicable rule: `COMPLIANT`, `NON-COMPLIANT`, `NEEDS ORGANIZER CLARIFICATION`, or `NOT APPLICABLE`, with required evidence and a blocking/nonblocking disposition.

## 10. Approval decisions needed from the team

Before installing the Rules Guardian, the team should approve or revise these interpretations:

1. Teensy is the competition safety/actuation authority; ESP32 is a temporary demo adapter or nonessential support device.
2. RC/Xbox/dashboard control is disabled or rejected in competition mode.
3. Course E-stop reaches Teensy through an independent fail-safe path.
4. Guarded automatic resume is the preferred competition behavior after E-stop clear.
5. Manual teach-and-repeat on the competition course is treated as unapproved until organizers answer.
6. Visual start and autonomous lap stop are mandatory autonomy features.
7. The August 14 demo is limited to an autonomous low-speed L path with one 90-degree turn.

Once these interpretations are approved, they can become enforceable repository guardrails instead of advisory notes.

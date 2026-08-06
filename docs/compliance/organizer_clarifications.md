# LAKSA Organizer Clarification Register

**Rules source:** revision 4.2, July 8, 2026
**Last reviewed:** August 6, 2026

An item remains open until the team records a dated written organizer response or a newer official rule revision that answers it. Verbal guidance may guide a test but must not close a competition gate.

| ID | Priority | Rules | Status | Question | Blocking effect |
|---|---|---|---|---|---|
| `CLAR-001` | P0 | Timeline; 0.2.5 | `OPEN` | Is the mandatory safety review September 23 or September 25, 2026, and what is the site-specific time? | Blocks schedule freeze, not normal development. |
| `CLAR-002` | P0 | 0.2.5.2; 1.2 | `OPEN` | Which heartbeat must be demonstrated: auxiliary wireless E-stop, Jetson-to-Teensy watchdog, or another interface? | Blocks safety-review signoff; implement Jetson command timeout regardless as an internal safety gate. |
| `CLAR-003` | P0 | 2.4; 3.4.1 | `OPEN` | Must RC/Wi-Fi/Bluetooth radios be electrically disabled, or is rejection of all control commands sufficient? Is outbound-only telemetry permitted? | Blocks final competition-mode communications configuration. |
| `CLAR-004` | P0 | 2.5.1; 3.4 | `OPEN` | Provide the final 2026 visual indicator's appearance, background, states, transition timing, illumination, placement, viewing distance, and sample/test artifact. | Blocks final detector thresholds and acceptance tests. A configurable interface and synthetic tests may proceed. |
| `CLAR-005` | P1 | 3.4.1 | `OPEN` | Which manual trigger methods are permitted for the five-second-penalty start? | Blocks implementation of the manual-start fallback. |
| `CLAR-006` | P1 | 1.2.10; 3.5.5 | `OPEN` | After course E-stop clear, is guarded automatic resume expected; are there delay or indication requirements? | Blocks final resume policy. Safe state-machine scaffolding may proceed. |
| `CLAR-007` | P1 | 2.4; 4.1.1 | `OPEN` | During the practice heat, may the team manually drive to collect a map/taught path, or must all on-course motion be autonomous? | Blocks on-course manual teach-and-repeat as a competition strategy. |
| `CLAR-008` | P1 | 2.1.2 | `OPEN` | Is the ZED 2i the provided perception sensor excluded from the Cat-funded $1,000 budget, and does the exemption apply to one specified unit? | Blocks final budget evidence, not sensor-only development. |
| `CLAR-009` | P1 | 1.2.2.1–1.2.2.4 | `OPEN` | What voltage/current may the robot apply to the course RJ45 contact interface, are all eight conductors present end-to-end, and are isolation or polarity constraints specified? | Blocks final interface electronics and connection to Teensy. |
| `CLAR-010` | P1 | 2.2.1; 2.6.10 | `OPEN` | Confirm that only the issued flag and its flexible wire are exempt from envelope/weight, while the mount, mast, sensors, and other hardware are not. | Blocks final mechanical compliance signoff. |
| `CLAR-011` | P2 | 3.2 | `OPEN` | When will the course layout and intersection instructions be frozen, and can they change after practice begins? | Blocks final route/map freeze. |
| `CLAR-012` | P2 | 3.7.3.1 | `OPEN` | Confirm the final nominal obstacle penalty and its publication date. | Blocks final skip/retry strategy optimization. |

## Response-record template

When an answer is received, add the following beneath the table and update the row status:

```text
Clarification ID:
Date received:
Organizer/source:
Permanent link or archived evidence:
Exact rule revision affected:
Answer summary:
Design consequence:
Rule-register entries updated:
Reviewer:
```

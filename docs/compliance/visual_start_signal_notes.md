# Visual Start/Stop Signal — Provisional Engineering Notes

**Evidence status:** prior-year organizer drawing supplied August 6, 2026
**Authority:** informational only; it does not freeze the 2026 detector

## Observed geometry

| Property | Value shown in drawing |
|---|---:|
| Background panel | 559 × 1219 mm |
| Signal center height | 813 mm from panel bottom |
| Each pinwheel section | 610 mm long |
| Central bar width | 102 mm |
| End-lobe radius | 102 mm |
| Relative orientation | Two sections fixed 90° out of phase |
| Colors | Satin Leaf Green and Satin Poppy Red |
| Track placement | Panel edge aligned with right-side straw bales |

## Not specified for 2026

- final background appearance and contrast;
- which visible state means start or stop;
- whether and how the mechanism rotates;
- transition timing and required temporal response;
- illumination, shadows, glare, and viewing distance;
- permitted false-positive/false-negative behavior;
- whether a sample or calibration artifact will be available.

## Development rule

Implement only a configurable detector interface and offline/synthetic tests until `CLAR-004` is closed. Do not hardcode final hue thresholds, geometry, state mapping, timing, or a single fixed region of interest from this drawing.

The detector must expose at least:

- timestamp;
- candidate state;
- confidence;
- temporal qualification state;
- reason for rejection/unknown;
- configuration/version identifier.

The mission state machine must treat `UNKNOWN`, stale detections, and contradictory detections as **do not start**.

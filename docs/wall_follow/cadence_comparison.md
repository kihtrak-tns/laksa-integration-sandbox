# Headless evidence cadence comparison

Both result sets are preserved. They are simulation evidence only.

| Evidence | Controller input/request cadence | Gym cadence | Corridor traversal | Safe-stop/fault cases | Corner completion | Lap completion |
|---|---:|---:|---:|---:|---:|---:|
| `results/wall_follow` at source `e34eb133070c4869c9b345c73fddf4ad24e220ed`, config SHA-256 `7597ea51333d9e9cb6a15f3c2f807ba9666aa4b25d09e77695a564aaaee04ea0` | 100 Hz | 100 Hz | 60/60 | 8/8 | not exercised | not exercised |
| `results/wall_follow_20hz` at source `72fe7464a2e6d0c4fcfc6b788ac191682c46ea2f`, config SHA-256 `b1fa0b84e1b36a947eae3f59dfb55651fc50a74684aa6534b4280e14698913e7` | 20 Hz | 100 Hz | 60/60 | 10/10, including 2/2 explicit safe stops | 15/15 | `UNVERIFIED` (0 runs) |

The current campaign's nominal controller-update rate was 19.65-19.80 Hz; its
request publication rate was 20 Hz. The small update-rate reduction comes from
the terminal scan tick, where the episode authority publishes the stop instead
of invoking the controller. The opening-obstacle case requested zero in 0.01 s,
reached zero applied simulated speed in 0.12 s over 0.0153 m, retained 0.0836 m
minimum full-body clearance, and had zero collisions. It intentionally stopped
and did not count as a corridor, corner, or lap completion.

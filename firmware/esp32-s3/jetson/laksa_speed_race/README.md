# LAKSA Competition Speed Race

This directory is an isolated **competition-only** integration area. It does
not modify the recovered mapping stack, Navigation V2, ESP32 firmware, or the
physical command path.

The C1 simulation-only pipeline is:

```text
canonical Speed Course -> Waterloo minimum-curvature raceline
  -> F1TENTH Gym core + LAKSA_PROXY_V0
  -> /c1/odom -> Waterloo Pure Pursuit -> /c1/drive_request
  -> simulation-only stepping authority -> exactly three laps -> terminal zero
```

`/sim_ground_truth_map` is reserved for simulator truth and is never an input
to mapping, localization, raceline generation, or race control.

## Current checkpoint

C0 is complete: exact external refs and licenses are pinned in
[`speed_race_upstream.repos`](speed_race_upstream.repos), and
[`UPSTREAM_PROVENANCE.md`](UPSTREAM_PROVENANCE.md) records the selection
evidence. C1 has a recovered canonical course, deterministic Waterloo
raceline, LAKSA_PROXY_V0, Gym-core adapter, three-lap gate, metrics, isolation
tests and reproducible container definitions. No simulator/controller
mathematics is reimplemented.

Official command on a Docker-capable host:

```bash
LAKSA_GIT_SHA=$(git rev-parse HEAD) docker compose -f docker-compose.c1.yaml up --build --abort-on-container-exit runtime
```

The current macOS host has no Docker or ROS 2 Humble runtime. Direct pinned-Gym
construction and one headless KS step pass, but official three-run evidence is
still pending and is not fabricated.

See [`SPEED_RACE_RESULTS.json`](SPEED_RACE_RESULTS.json) for machine-readable
status and exact blockers. Do not launch any legacy manual-control, joystick,
or physical actuation package from this directory.

## Wall-follow simulation and mock

Issue #2 adds a separate scan-driven, simulation-only boundary. The controller,
Gym mock, map generator, replay tool, and fault campaign use only
`/sim/laksa/*`; they contain no physical `DriveCommand` publisher. Exact
assumptions live in `config/wall_follow_v1.json`. The model card and promotion
gate are in `docs/wall_follow/model_card.md` and
`docs/wall_follow/integration_gate.md` at repository root.

Run the portable tests with:

```bash
python -m unittest discover -s test -p 'test_wall_follow_*.py' -v
```

Run the pinned-Gym campaign using the command in the integration note. Current
10 mm-map evidence is written to `results/wall_follow_10mm`; historical 20 Hz
evidence remains in `results/wall_follow_20hz`, and original 100 Hz evidence
remains in `results/wall_follow` for comparison. Generated map images are
omitted because the deterministic generator and SHA-256 values are committed.

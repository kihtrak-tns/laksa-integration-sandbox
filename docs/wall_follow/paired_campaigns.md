# Paired wall-follow campaigns

This extends Issue #2 / draft PR #3. It evaluates changes against the recorded
85-case pinned-Gym campaign before any Unity/AutoDRIVE adapter is considered.
It operates only on simulation manifests and cannot publish a car command.

## Run and compare

From `firmware/esp32-s3/jetson/laksa_speed_race`, with the pinned Gym and its
locked Python dependencies installed in an isolated environment:

```sh
python -m laksa_speed_race.wall_follow_sim \
  --config config/wall_follow_v1.json \
  --source-sha "$(git rev-parse HEAD)" \
  --output-dir /tmp/laksa-candidate
python -m laksa_speed_race.wall_follow_compare \
  results/wall_follow_10mm/run_manifest.json \
  /tmp/laksa-candidate/run_manifest.json \
  --candidate-maps-dir /tmp/laksa-candidate/maps \
  --output /tmp/laksa-comparison.json
```

The comparator rejects changed map content, simulator pin, case list, or
duplicate case IDs. The optional map directory verifies the candidate's file
hash and proves that its LF bytes become the recorded Windows baseline hash
when only newlines are converted to CRLF. Without that proof, mismatched hashes
are rejected. It pairs by map, seed, pose, and injected fault. Exit 0
means no regression against the baseline by its stated tolerances; exit 2 means
a detected regression or invalid comparison. It checks lost completions,
increased collisions, >5 mm loss of sampled clearance, >50 ms extra
stop-request-to-zero-applied time, and >20 mm extra distance after a stop
request. Report counts by scenario class keep a safe stop separate from
corridor/corner completion. Both reports expose individual cases for review.

`--source-sha` in the runner is supplied by the operator, not independently
attested. Preserve the tested checkout SHA, the environment's pinned Gym SHA,
the exact config and map hashes, and the comparison JSON together. A later
Docker/ROS run needs a build-time source-to-image record to clear PR #3's
existing provenance gate. Comparing a manifest against itself only checks the
comparator; it is not new simulation evidence.

## 2026-10-02 isolated rerun

- Runner checkout: `2146354b08e98a7e86015d0de97bc909aeaf295a`;
  pinned Gym checkout verified at `bdaec1420c3b0f103858d289866d0d4e2e597c30`.
- Linux Python 3.12 virtual environment installed the committed
  `docker/requirements-runtime.lock`; the campaign used the unchanged
  `config/wall_follow_v1.json` SHA-256
  `b1fa0b84e1b36a947eae3f59dfb55651fc50a74684aa6534b4280e14698913e7`.
- `29` focused tests passed. New Gym campaign: `75/75` nominal and `10/10`
  fault cases passed, zero collisions. Paired comparison: `85` cases,
  `0` regressions; map content verified against the historical Windows hashes
  by LF-to-CRLF conversion. The two safe stops are not completions.
- [Fresh run manifest](../../firmware/esp32-s3/jetson/laksa_speed_race/results/wall_follow_compare_20261002/run_manifest.json)
  and [paired report](../../firmware/esp32-s3/jetson/laksa_speed_race/results/wall_follow_compare_20261002/comparison.json).

This reruns the same controller/configuration to prove the comparison harness
and cross-platform reproducibility. It measures no controller improvement and
does not clear PR #3's ROS image provenance, real scan replay, race-lap, or
physical-car gates.

## Next integration boundary

The Unity course builder should export versioned course geometry and obstacle
poses. The AutoDRIVE adapter should produce the same portable scan, odometry,
and bounded motion-request semantics as the Gym mock. Compare controllers
within each simulator on matched scenarios; never declare a direct paired
comparison between different maps, physics, or sensor models. Calibration
requires real logs. No closed race lap, obstacle terrain, physical braking,
or emergency-stop behavior is established by these campaigns.

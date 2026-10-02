"""Compare two isolated Gym campaigns without conflating stops and completions."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


IDENTITY = ("map", "seed", "pose_id", "fault")
STOP_METRICS = (
    ("time_from_stop_request_to_zero_applied_s", 0.05),
    ("distance_after_stop_request_m", 0.02),
)


def _indexed(manifest: dict[str, Any]) -> dict[tuple[Any, ...], dict[str, Any]]:
    result: dict[tuple[Any, ...], dict[str, Any]] = {}
    for run in manifest["runs"]:
        key = tuple(run[field] for field in IDENTITY)
        if key in result:
            raise ValueError(f"duplicate case: {key}")
        result[key] = run
    return result


def _map_hashes(manifest: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {name: record["files"] for name, record in manifest["maps"].items()}


def _aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        groups[run["scenario_class"]].append(run)
    return {
        name: {
            "runs": len(items),
            "passed": sum(item["verdict"] == "PASS" for item in items),
            "completed": sum(bool(item["completion"]) for item in items),
            "collisions": sum(item["collision_count"] for item in items),
            "minimum_estimated_clearance_m": min(item["minimum_perimeter_sampled_clearance_m"] for item in items),
        }
        for name, items in sorted(groups.items())
    }


def _check_maps(
    baseline: dict[str, Any], candidate: dict[str, Any], candidate_maps_dir: Path | None
) -> str:
    if _map_hashes(baseline) == _map_hashes(candidate):
        return "byte_identical"
    if candidate_maps_dir is None:
        raise ValueError("map hashes differ; this is not a paired controller comparison")
    if baseline["maps"].keys() != candidate["maps"].keys():
        raise ValueError("map set differs")
    for name, old_map in baseline["maps"].items():
        new_map = candidate["maps"][name]
        if old_map["profile"] != new_map["profile"] or old_map["rendered_entry_width_m"] != new_map["rendered_entry_width_m"]:
            raise ValueError(f"map geometry differs: {name}")
        if old_map["files"].keys() != new_map["files"].keys():
            raise ValueError(f"map file set differs: {name}")
        for filename, old_hash in old_map["files"].items():
            if Path(filename).name != filename:
                raise ValueError("map file name must be a basename")
            raw = (candidate_maps_dir / name / filename).read_bytes()
            if hashlib.sha256(raw).hexdigest() != new_map["files"][filename]:
                raise ValueError(f"candidate map file does not match its manifest: {name}/{filename}")
            if b"\r" in raw or b"\n" not in raw:
                raise ValueError(f"map is not LF text: {name}/{filename}")
            windows_hash = hashlib.sha256(raw.replace(b"\n", b"\r\n")).hexdigest()
            if windows_hash != old_hash:
                raise ValueError(f"map content differs beyond LF/CRLF: {name}/{filename}")
    return "verified_lf_vs_crlf"


def compare(
    baseline: dict[str, Any], candidate: dict[str, Any], candidate_maps_dir: Path | None = None
) -> dict[str, Any]:
    """Require identical scenarios and maps; assess per-case safety regressions."""
    if baseline.get("schema_version") != candidate.get("schema_version"):
        raise ValueError("campaign schema differs")
    if baseline.get("upstream") != candidate.get("upstream"):
        raise ValueError("pinned simulator versions differ")
    map_comparison = _check_maps(baseline, candidate, candidate_maps_dir)
    before, after = _indexed(baseline), _indexed(candidate)
    if before.keys() != after.keys():
        raise ValueError(f"scenario keys differ: missing={len(before.keys() - after.keys())}, extra={len(after.keys() - before.keys())}")
    regressions = []
    for key in sorted(before, key=str):
        old, new = before[key], after[key]
        reasons = []
        if old["scenario_class"] != new["scenario_class"]:
            reasons.append("scenario_class_changed")
        if old["verdict"] == "PASS" and new["verdict"] != "PASS":
            reasons.append("lost_pass")
        if old["completion"] and not new["completion"]:
            reasons.append("lost_completion")
        if new["collision_count"] > old["collision_count"]:
            reasons.append("more_collisions")
        if new["minimum_perimeter_sampled_clearance_m"] < old["minimum_perimeter_sampled_clearance_m"] - 0.005:
            reasons.append("clearance_drop_over_5mm")
        if new["scenario_class"] == "safe_stop" and new["completion"]:
            reasons.append("safe_stop_mislabeled_completion")
        for field, tolerance in STOP_METRICS:
            old_value, new_value = old.get(field), new.get(field)
            if old_value is not None and new_value is None:
                reasons.append(f"missing_{field}")
            elif old_value is not None and new_value is not None and new_value > old_value + tolerance + 1e-9:
                reasons.append(f"increased_{field}")
        if reasons:
            regressions.append({"case": dict(zip(IDENTITY, key)), "reasons": reasons})
    return {
        "schema_version": "laksa-wall-follow-comparison-v1",
        "scope": "paired_simulation_only",
        "baseline_source_sha_declared": baseline.get("sandbox_source_sha"),
        "candidate_source_sha_declared": candidate.get("sandbox_source_sha"),
        "baseline_config_sha256": baseline.get("configuration_sha256"),
        "candidate_config_sha256": candidate.get("configuration_sha256"),
        "matched_cases": len(before),
        "map_comparison": map_comparison,
        "baseline": _aggregate(list(before.values())),
        "candidate": _aggregate(list(after.values())),
        "regressions": regressions,
        "gate": "PASS" if not regressions else "REGRESSION",
        "limitations": [
            "Manifests declare source hashes but do not attest the build or installed Gym image.",
            "Perimeter clearance is sampled, and simulation does not validate physical stopping.",
            "A safe stop is not a completed route; these campaigns contain no race lap.",
        ],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--candidate-maps-dir", type=Path, help="Verify candidate LF files against baseline CRLF hashes")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = compare(
            json.loads(args.baseline.read_text(encoding="utf-8")),
            json.loads(args.candidate.read_text(encoding="utf-8")),
            args.candidate_maps_dir,
        )
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['gate']}: {report['matched_cases']} paired cases, {len(report['regressions'])} regressions")
    raise SystemExit(0 if report["gate"] == "PASS" else 2)


if __name__ == "__main__":
    main()

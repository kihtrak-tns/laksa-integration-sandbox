"""Deterministic text-map generation for isolated wall-follow Gym runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class CorridorMap:
    name: str
    width_m: float
    length_m: float = 8.0
    resolution_m: float = 0.02
    world_width_m: float = 9.0
    world_height_m: float = 4.0
    center_y_m: float = 2.0
    start_wall_x_m: float = 0.40
    end_wall_x_m: float = 8.40
    right_recess_start_m: float | None = None
    right_recess_end_m: float | None = None
    right_recess_depth_m: float = 0.0
    obstacle_x_m: float | None = None

    @property
    def bottom_y_m(self) -> float:
        return self.center_y_m - self.width_m / 2.0

    @property
    def top_y_m(self) -> float:
        return self.center_y_m + self.width_m / 2.0

    def right_boundary_y(self, x_m: float) -> float:
        if (
            self.right_recess_start_m is not None
            and self.right_recess_end_m is not None
            and self.right_recess_start_m <= x_m <= self.right_recess_end_m
        ):
            return self.bottom_y_m - self.right_recess_depth_m
        return self.bottom_y_m


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_corridor_map(profile: CorridorMap, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    width_px = round(profile.world_width_m / profile.resolution_m)
    height_px = round(profile.world_height_m / profile.resolution_m)
    rows: list[list[int]] = [[0 for _ in range(width_px)] for _ in range(height_px)]
    for py in range(height_px):
        y_m = (py + 0.5) * profile.resolution_m
        for px in range(width_px):
            x_m = (px + 0.5) * profile.resolution_m
            bottom = profile.right_boundary_y(x_m)
            free = (
                profile.start_wall_x_m < x_m < profile.end_wall_x_m
                and bottom < y_m < profile.top_y_m
            )
            if profile.obstacle_x_m is not None and abs(x_m - profile.obstacle_x_m) <= profile.resolution_m:
                free = False
            rows[py][px] = 255 if free else 0

    image_path = output_dir / f"{profile.name}.pgm"
    pgm_lines = ["P2", f"{width_px} {height_px}", "255"]
    # Map loaders flip the image vertically; write world-high rows first.
    pgm_lines.extend(" ".join(str(value) for value in row) for row in reversed(rows))
    image_path.write_text("\n".join(pgm_lines) + "\n", encoding="ascii")

    yaml_path = output_dir / f"{profile.name}_map.yaml"
    yaml_path.write_text(
        "\n".join(
            [
                f"image: {image_path.name}",
                f"resolution: {profile.resolution_m}",
                "origin: [0.0, 0.0, 0.0]",
                "negate: 0",
                "occupied_thresh: 0.65",
                "free_thresh: 0.196",
                "",
            ]
        ),
        encoding="utf-8",
    )
    centerline_path = output_dir / f"{profile.name}_centerline.csv"
    inset = min(0.20, profile.width_m * 0.38)
    centerline_path.write_text(
        "x_m,y_m\n"
        f"1.0,{profile.bottom_y_m + inset}\n"
        f"7.5,{profile.bottom_y_m + inset}\n"
        f"7.5,{profile.top_y_m - inset}\n"
        f"1.0,{profile.top_y_m - inset}\n"
        f"1.0,{profile.bottom_y_m + inset}\n",
        encoding="utf-8",
    )
    spec_path = output_dir / f"{profile.name}_spec.json"
    spec_path.write_text(json.dumps(asdict(profile), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "name": profile.name,
        "profile": asdict(profile),
        "map_stub": str(output_dir / profile.name),
        "files": {
            path.name: _sha256(path)
            for path in (image_path, yaml_path, centerline_path, spec_path)
        },
    }


def campaign_profiles() -> tuple[CorridorMap, ...]:
    inch = 0.0254
    return (
        CorridorMap(
            name="continuous_wall_30in",
            width_m=30.0 * inch,
            right_recess_start_m=3.0,
            right_recess_end_m=3.8,
            right_recess_depth_m=0.25,
        ),
        CorridorMap(name="continuous_wall_20in", width_m=20.0 * inch),
        CorridorMap(name="continuous_wall_19in", width_m=19.0 * inch),
        CorridorMap(name="continuous_wall_21in", width_m=21.0 * inch),
    )

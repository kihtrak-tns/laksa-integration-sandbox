"""Deterministic text-map generation for isolated wall-follow Gym runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
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

    def is_free(self, x_m: float, y_m: float) -> bool:
        free = (
            self.start_wall_x_m < x_m < self.end_wall_x_m
            and self.right_boundary_y(x_m) < y_m < self.top_y_m
        )
        if self.obstacle_x_m is not None and abs(x_m - self.obstacle_x_m) <= self.resolution_m:
            return False
        return free

    def point_clearance(self, x_m: float, y_m: float) -> float:
        clearance = min(
            y_m - self.right_boundary_y(x_m),
            self.top_y_m - y_m,
            x_m - self.start_wall_x_m,
            self.end_wall_x_m - x_m,
        )
        if self.obstacle_x_m is not None and x_m <= self.obstacle_x_m:
            clearance = min(clearance, self.obstacle_x_m - x_m)
        return clearance

    def centerline_points(self) -> tuple[tuple[float, float], ...]:
        inset = min(0.20, self.width_m * 0.38)
        return (
            (1.0, self.bottom_y_m + inset),
            (7.5, self.bottom_y_m + inset),
            (7.5, self.top_y_m - inset),
            (1.0, self.top_y_m - inset),
            (1.0, self.bottom_y_m + inset),
        )


@dataclass(frozen=True)
class CornerMap:
    """Smooth 90-degree left corner with a continuous observable right wall."""

    name: str = "continuous_wall_left_corner_30in"
    width_m: float = 30.0 * 0.0254
    resolution_m: float = 0.02
    world_width_m: float = 7.0
    world_height_m: float = 7.0
    entry_start_x_m: float = 0.40
    entry_y_m: float = 1.50
    turn_center_x_m: float = 3.00
    turn_center_y_m: float = 3.50
    turn_radius_m: float = 2.00
    exit_end_y_m: float = 6.40

    @staticmethod
    def _segment_distance(
        x_m: float,
        y_m: float,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> float:
        dx, dy = end[0] - start[0], end[1] - start[1]
        denominator = dx * dx + dy * dy
        projection = 0.0 if denominator == 0.0 else (
            (x_m - start[0]) * dx + (y_m - start[1]) * dy
        ) / denominator
        projection = max(0.0, min(1.0, projection))
        nearest_x = start[0] + projection * dx
        nearest_y = start[1] + projection * dy
        return math.hypot(x_m - nearest_x, y_m - nearest_y)

    def path_distance(self, x_m: float, y_m: float) -> float:
        entry_end = (self.turn_center_x_m, self.entry_y_m)
        exit_x = self.turn_center_x_m + self.turn_radius_m
        exit_start = (exit_x, self.turn_center_y_m)
        entry_distance = self._segment_distance(
            x_m, y_m, (self.entry_start_x_m, self.entry_y_m), entry_end,
        )
        exit_distance = self._segment_distance(
            x_m, y_m, exit_start, (exit_x, self.exit_end_y_m),
        )
        angle = math.atan2(y_m - self.turn_center_y_m, x_m - self.turn_center_x_m)
        clamped_angle = max(-math.pi / 2.0, min(0.0, angle))
        arc_x = self.turn_center_x_m + self.turn_radius_m * math.cos(clamped_angle)
        arc_y = self.turn_center_y_m + self.turn_radius_m * math.sin(clamped_angle)
        arc_distance = math.hypot(x_m - arc_x, y_m - arc_y)
        return min(entry_distance, arc_distance, exit_distance)

    def is_free(self, x_m: float, y_m: float) -> bool:
        return self.path_distance(x_m, y_m) < self.width_m / 2.0

    def point_clearance(self, x_m: float, y_m: float) -> float:
        return self.width_m / 2.0 - self.path_distance(x_m, y_m)

    def centerline_points(self) -> tuple[tuple[float, float], ...]:
        points: list[tuple[float, float]] = [
            (self.entry_start_x_m, self.entry_y_m),
            (self.turn_center_x_m, self.entry_y_m),
        ]
        for index in range(1, 13):
            angle = -math.pi / 2.0 + index * (math.pi / 2.0) / 12.0
            points.append(
                (
                    self.turn_center_x_m + self.turn_radius_m * math.cos(angle),
                    self.turn_center_y_m + self.turn_radius_m * math.sin(angle),
                )
            )
        points.append((self.turn_center_x_m + self.turn_radius_m, self.exit_end_y_m))
        return tuple(points)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_corridor_map(profile: CorridorMap | CornerMap, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    width_px = round(profile.world_width_m / profile.resolution_m)
    height_px = round(profile.world_height_m / profile.resolution_m)
    rows: list[list[int]] = [[0 for _ in range(width_px)] for _ in range(height_px)]
    for py in range(height_px):
        y_m = (py + 0.5) * profile.resolution_m
        for px in range(width_px):
            x_m = (px + 0.5) * profile.resolution_m
            rows[py][px] = 255 if profile.is_free(x_m, y_m) else 0

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
    centerline_rows = ["x_m,y_m"]
    centerline_rows.extend(f"{x_m},{y_m}" for x_m, y_m in profile.centerline_points())
    centerline_path.write_text("\n".join(centerline_rows) + "\n", encoding="utf-8")
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


def corner_profiles() -> tuple[CornerMap, ...]:
    return (CornerMap(),)

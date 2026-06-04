"""MVP mounting-plate feature evaluator."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from legacy_part_bench.dataset import HoleFeature, PartMetadata
from legacy_part_bench.evaluators.bbox_eval import CategoryScore, _coerce_mesh, load_stl_geometry


@dataclass(frozen=True)
class HoleDetection:
    """Heuristic detection result for one expected through hole."""

    expected_center: tuple[float, float]
    expected_diameter: float
    detected: bool
    radial_vertex_count: int
    angular_bins_hit: int
    z_levels_hit: int
    radial_tolerance: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_features(
    generated_stl_path: Path | str,
    metadata: PartMetadata,
    *,
    max_score: float = 35.0,
) -> CategoryScore:
    """Score expected MVP through holes in a generated mounting-plate STL."""

    if metadata.family != "mounting_plate":
        return CategoryScore(
            score=0.0,
            max_score=max_score,
            details={"error": f"Unsupported part family: {metadata.family}"},
        )

    expected_holes = list(metadata.features.holes)
    if not expected_holes:
        return CategoryScore(
            score=max_score,
            max_score=max_score,
            details={
                "expected_holes": 0,
                "detected_expected_holes": 0,
                "missed_holes": [],
            },
        )

    geometry = load_stl_geometry(generated_stl_path)
    if not geometry.loadable:
        return CategoryScore(
            score=0.0,
            max_score=max_score,
            details={
                "expected_holes": len(expected_holes),
                "detected_expected_holes": 0,
                "missed_holes": [list(hole.center) for hole in expected_holes],
                "generated_geometry": geometry.to_dict(),
                "error": geometry.error or "Generated STL could not be loaded.",
            },
        )

    try:
        mesh = _load_mesh(generated_stl_path)
    except Exception as exc:  # noqa: BLE001 - scorecards should survive bad meshes.
        return CategoryScore(
            score=0.0,
            max_score=max_score,
            details={
                "expected_holes": len(expected_holes),
                "detected_expected_holes": 0,
                "missed_holes": [list(hole.center) for hole in expected_holes],
                "generated_geometry": geometry.to_dict(),
                "error": f"{exc.__class__.__name__}: {exc}",
            },
        )

    detections = [_detect_expected_hole(mesh, hole, metadata) for hole in expected_holes]
    detected = [detection for detection in detections if detection.detected]
    missed = [
        list(detection.expected_center)
        for detection in detections
        if not detection.detected
    ]
    score = max_score * (len(detected) / len(expected_holes))

    return CategoryScore(
        score=score,
        max_score=max_score,
        details={
            "expected_holes": len(expected_holes),
            "detected_expected_holes": len(detected),
            "missed_holes": missed,
            "detections": [detection.to_dict() for detection in detections],
            "generated_geometry": geometry.to_dict(),
            "heuristic": (
                "Detects expected through holes by looking for mesh vertices on the "
                "expected circular wall with broad angular coverage and vertices near "
                "both top and bottom surfaces."
            ),
        },
    )


def _detect_expected_hole(
    mesh: trimesh.Trimesh,
    hole: HoleFeature,
    metadata: PartMetadata,
) -> HoleDetection:
    center = np.array(hole.center, dtype=float)
    vertices = np.asarray(mesh.vertices, dtype=float)
    xy = vertices[:, :2]
    z = vertices[:, 2]
    radius = hole.diameter / 2.0
    radial_tolerance = max(0.35, hole.diameter * 0.08)
    radial_distance = np.linalg.norm(xy - center, axis=1)
    near_wall = np.abs(radial_distance - radius) <= radial_tolerance

    thickness = metadata.dimensions.thickness
    z_tolerance = max(0.35, thickness * 0.08)
    near_bottom = z <= z.min() + z_tolerance
    near_top = z >= z.max() - z_tolerance
    through_z = near_bottom | near_top
    candidates = vertices[near_wall & through_z]

    angular_bins_hit = 0
    z_levels_hit = 0
    if len(candidates) > 0:
        candidate_xy = candidates[:, :2]
        angles = np.arctan2(candidate_xy[:, 1] - center[1], candidate_xy[:, 0] - center[0])
        bins = np.floor(((angles + np.pi) / (2.0 * np.pi)) * 12).astype(int)
        angular_bins_hit = int(len(set(np.clip(bins, 0, 11))))
        candidate_z = candidates[:, 2]
        z_levels_hit = int(np.any(candidate_z <= z.min() + z_tolerance)) + int(
            np.any(candidate_z >= z.max() - z_tolerance)
        )

    detected = bool(len(candidates) >= 8 and angular_bins_hit >= 6 and z_levels_hit == 2)
    return HoleDetection(
        expected_center=hole.center,
        expected_diameter=hole.diameter,
        detected=detected,
        radial_vertex_count=int(len(candidates)),
        angular_bins_hit=angular_bins_hit,
        z_levels_hit=z_levels_hit,
        radial_tolerance=radial_tolerance,
    )


def _load_mesh(stl_path: Path | str) -> trimesh.Trimesh:
    return _coerce_mesh(trimesh.load_mesh(Path(stl_path), force="mesh"))

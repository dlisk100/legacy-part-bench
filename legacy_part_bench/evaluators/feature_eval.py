"""Feature evaluators for benchmark part metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from legacy_part_bench.dataset import HoleFeature, PartMetadata, SlotFeature
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


@dataclass(frozen=True)
class SlotDetection:
    """Heuristic detection result for one expected horizontal through-slot."""

    expected_center: tuple[float, float]
    expected_length: float
    expected_width: float
    detected: bool
    boundary_vertex_count: int
    x_regions_hit: int
    z_levels_hit: int
    boundary_tolerance: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_features(
    generated_stl_path: Path | str,
    metadata: PartMetadata,
    *,
    max_score: float = 35.0,
) -> CategoryScore:
    """Score expected holes and slots with deterministic MVP heuristics."""

    expected_holes = list(metadata.features.holes)
    expected_slots = list(metadata.features.slots)
    expected_feature_count = len(expected_holes) + len(expected_slots)
    if expected_feature_count == 0:
        return CategoryScore(
            score=max_score,
            max_score=max_score,
            details={
                "family": metadata.family,
                "expected_holes": 0,
                "detected_expected_holes": 0,
                "expected_slots": 0,
                "detected_expected_slots": 0,
                "missed_holes": [],
                "missed_slots": [],
                "note": "No explicit feature checks were required for this part.",
            },
        )

    geometry = load_stl_geometry(generated_stl_path)
    if not geometry.loadable:
        return CategoryScore(
            score=0.0,
            max_score=max_score,
            details={
                "family": metadata.family,
                "expected_holes": len(expected_holes),
                "detected_expected_holes": 0,
                "expected_slots": len(expected_slots),
                "detected_expected_slots": 0,
                "missed_holes": [list(hole.center) for hole in expected_holes],
                "missed_slots": [list(slot.center) for slot in expected_slots],
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
                "family": metadata.family,
                "expected_holes": len(expected_holes),
                "detected_expected_holes": 0,
                "expected_slots": len(expected_slots),
                "detected_expected_slots": 0,
                "missed_holes": [list(hole.center) for hole in expected_holes],
                "missed_slots": [list(slot.center) for slot in expected_slots],
                "generated_geometry": geometry.to_dict(),
                "error": f"{exc.__class__.__name__}: {exc}",
            },
        )

    hole_detections = [_detect_expected_hole(mesh, hole, metadata) for hole in expected_holes]
    slot_detections = [_detect_expected_slot(mesh, slot, metadata) for slot in expected_slots]
    detected_holes = [detection for detection in hole_detections if detection.detected]
    detected_slots = [detection for detection in slot_detections if detection.detected]
    missed = [
        list(detection.expected_center)
        for detection in hole_detections
        if not detection.detected
    ]
    missed_slots = [
        list(detection.expected_center)
        for detection in slot_detections
        if not detection.detected
    ]
    detected_feature_count = len(detected_holes) + len(detected_slots)
    score = max_score * (detected_feature_count / expected_feature_count)

    return CategoryScore(
        score=score,
        max_score=max_score,
        details={
            "family": metadata.family,
            "expected_holes": len(expected_holes),
            "detected_expected_holes": len(detected_holes),
            "expected_slots": len(expected_slots),
            "detected_expected_slots": len(detected_slots),
            "missed_holes": missed,
            "missed_slots": missed_slots,
            "detections": [detection.to_dict() for detection in hole_detections],
            "hole_detections": [detection.to_dict() for detection in hole_detections],
            "slot_detections": [detection.to_dict() for detection in slot_detections],
            "generated_geometry": geometry.to_dict(),
            "heuristic": (
                "Detects expected through holes and horizontal through-slots by looking "
                "for mesh vertices on the expected cut walls with broad XY coverage and "
                "vertices near both local through-cut surfaces."
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

    z_bottom, z_top = _local_through_z_range(metadata)
    z_tolerance = max(0.35, (z_top - z_bottom) * 0.08)
    near_bottom = np.abs(z - (z.min() + z_bottom)) <= z_tolerance
    near_top = np.abs(z - (z.min() + z_top)) <= z_tolerance
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
        z_levels_hit = int(np.any(np.abs(candidate_z - (z.min() + z_bottom)) <= z_tolerance)) + int(
            np.any(np.abs(candidate_z - (z.min() + z_top)) <= z_tolerance)
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


def _detect_expected_slot(
    mesh: trimesh.Trimesh,
    slot: SlotFeature,
    metadata: PartMetadata,
) -> SlotDetection:
    center = np.array(slot.center, dtype=float)
    vertices = np.asarray(mesh.vertices, dtype=float)
    xy = vertices[:, :2]
    z = vertices[:, 2]
    radius = slot.width / 2.0
    straight_half_length = max(0.0, (slot.length - slot.width) / 2.0)
    boundary_tolerance = max(0.35, slot.width * 0.08)

    relative = xy - center
    dx = np.abs(relative[:, 0])
    dy = np.abs(relative[:, 1])
    straight_region = dx <= straight_half_length
    straight_distance = np.abs(dy - radius)
    end_distance = np.abs(np.sqrt((dx - straight_half_length) ** 2 + dy**2) - radius)
    boundary_distance = np.where(straight_region, straight_distance, end_distance)
    near_boundary = boundary_distance <= boundary_tolerance

    z_bottom, z_top = _local_through_z_range(metadata)
    z_tolerance = max(0.35, (z_top - z_bottom) * 0.08)
    near_bottom = np.abs(z - (z.min() + z_bottom)) <= z_tolerance
    near_top = np.abs(z - (z.min() + z_top)) <= z_tolerance
    candidates = vertices[near_boundary & (near_bottom | near_top)]

    x_regions_hit = 0
    z_levels_hit = 0
    if len(candidates) > 0:
        candidate_x = candidates[:, 0] - center[0]
        left = candidate_x <= -straight_half_length + boundary_tolerance
        middle = np.abs(candidate_x) < straight_half_length * 0.65
        right = candidate_x >= straight_half_length - boundary_tolerance
        x_regions_hit = int(np.any(left)) + int(np.any(middle)) + int(np.any(right))
        candidate_z = candidates[:, 2]
        z_levels_hit = int(np.any(np.abs(candidate_z - (z.min() + z_bottom)) <= z_tolerance)) + int(
            np.any(np.abs(candidate_z - (z.min() + z_top)) <= z_tolerance)
        )

    detected = bool(len(candidates) >= 10 and x_regions_hit >= 2 and z_levels_hit == 2)
    return SlotDetection(
        expected_center=slot.center,
        expected_length=slot.length,
        expected_width=slot.width,
        detected=detected,
        boundary_vertex_count=int(len(candidates)),
        x_regions_hit=x_regions_hit,
        z_levels_hit=z_levels_hit,
        boundary_tolerance=boundary_tolerance,
    )


def _local_through_z_range(metadata: PartMetadata) -> tuple[float, float]:
    if metadata.family == "l_bracket":
        flange_thickness = metadata.parameters.get("flange_thickness")
        if isinstance(flange_thickness, (int, float)):
            return 0.0, float(flange_thickness)
    return 0.0, metadata.dimensions.thickness


def _load_mesh(stl_path: Path | str) -> trimesh.Trimesh:
    return _coerce_mesh(trimesh.load_mesh(Path(stl_path), force="mesh"))

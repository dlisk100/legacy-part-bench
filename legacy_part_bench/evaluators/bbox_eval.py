"""Bounding-box geometry loading and scoring helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from legacy_part_bench.dataset import PartMetadata


@dataclass(frozen=True)
class GeometryMetrics:
    """Load result for one STL mesh."""

    path: str
    exists: bool
    loadable: bool
    mesh_valid: bool
    watertight: bool
    extents: tuple[float, float, float] | None
    volume: float | None
    vertex_count: int = 0
    face_count: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CategoryScore:
    """One JSON-serializable scorecard category."""

    score: float
    max_score: float
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 6),
            "max_score": self.max_score,
            "details": self.details,
        }


def load_stl_geometry(stl_path: Path | str) -> GeometryMetrics:
    """Load an STL file and compute basic mesh metrics."""

    path = Path(stl_path)
    if not path.exists():
        return GeometryMetrics(
            path=str(path),
            exists=False,
            loadable=False,
            mesh_valid=False,
            watertight=False,
            extents=None,
            volume=None,
            error="STL file does not exist.",
        )

    try:
        loaded = trimesh.load_mesh(path, force="mesh")
        mesh = _coerce_mesh(loaded)
        if mesh.vertices.size == 0 or mesh.faces.size == 0:
            raise ValueError("STL did not contain mesh vertices and faces.")

        extents = tuple(float(value) for value in mesh.extents)
        volume = float(abs(mesh.volume))
        mesh_valid = bool(mesh.is_volume or mesh.is_watertight or volume > 0.0)
        return GeometryMetrics(
            path=str(path),
            exists=True,
            loadable=True,
            mesh_valid=mesh_valid,
            watertight=bool(mesh.is_watertight),
            extents=extents,
            volume=volume,
            vertex_count=int(len(mesh.vertices)),
            face_count=int(len(mesh.faces)),
        )
    except Exception as exc:  # noqa: BLE001 - structured scoring failure boundary.
        return GeometryMetrics(
            path=str(path),
            exists=True,
            loadable=False,
            mesh_valid=False,
            watertight=False,
            extents=None,
            volume=None,
            error=f"{exc.__class__.__name__}: {exc}",
        )


def evaluate_bounding_box(
    generated_stl_path: Path | str,
    metadata: PartMetadata,
    *,
    max_score: float = 20.0,
    zero_at_relative_error: float = 0.20,
) -> CategoryScore:
    """Score generated STL extents against metadata dimensions."""

    geometry = load_stl_geometry(generated_stl_path)
    target_extents = (
        metadata.dimensions.length,
        metadata.dimensions.width,
        metadata.dimensions.thickness,
    )
    if not geometry.loadable or geometry.extents is None:
        return CategoryScore(
            score=0.0,
            max_score=max_score,
            details={
                "target_extents": list(target_extents),
                "generated_geometry": geometry.to_dict(),
                "error": geometry.error or "Generated STL could not be loaded.",
            },
        )

    generated_extents = geometry.extents
    relative_errors = [
        abs(generated - target) / target
        for generated, target in zip(generated_extents, target_extents, strict=True)
    ]
    dimension_scores = [
        max(0.0, 1.0 - relative_error / zero_at_relative_error)
        for relative_error in relative_errors
    ]
    score = float(np.mean(dimension_scores) * max_score)

    return CategoryScore(
        score=score,
        max_score=max_score,
        details={
            "target_extents": list(target_extents),
            "generated_extents": list(generated_extents),
            "relative_errors": relative_errors,
            "dimension_scores": dimension_scores,
            "generated_geometry": geometry.to_dict(),
        },
    )


def _coerce_mesh(loaded: Any) -> trimesh.Trimesh:
    if isinstance(loaded, trimesh.Scene):
        meshes = [geometry for geometry in loaded.geometry.values() if isinstance(geometry, trimesh.Trimesh)]
        if not meshes:
            raise ValueError("Scene did not contain any mesh geometry.")
        return trimesh.util.concatenate(meshes)
    if not isinstance(loaded, trimesh.Trimesh):
        raise TypeError(f"Unsupported geometry type: {type(loaded).__name__}")
    return loaded

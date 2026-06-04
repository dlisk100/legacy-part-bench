"""CadQuery generator for the MVP mounting-plate part family."""

from pathlib import Path
from typing import Any

from legacy_part_bench.dataset import BenchmarkItem, PartMetadata, save_metadata

_CUTTER_MARGIN_MM = 1.0


def build_mounting_plate(metadata: PartMetadata) -> Any:
    """Build a rectangular mounting plate with through holes from metadata."""

    _validate_mounting_plate_metadata(metadata)
    cq = _import_cadquery()

    dimensions = metadata.dimensions
    part = cq.Workplane("XY").box(
        dimensions.length,
        dimensions.width,
        dimensions.thickness,
        centered=(False, False, False),
    )

    for hole in metadata.features.holes:
        cutter = (
            cq.Workplane("XY")
            .center(hole.center[0], hole.center[1])
            .circle(hole.diameter / 2.0)
            .extrude(dimensions.thickness + 2.0 * _CUTTER_MARGIN_MM)
            .translate((0.0, 0.0, -_CUTTER_MARGIN_MM))
        )
        part = part.cut(cutter)

    return part


def export_mounting_plate(metadata: PartMetadata, output_dir: Path | str) -> BenchmarkItem:
    """Write metadata and target CAD artifacts for one mounting plate."""

    _validate_mounting_plate_metadata(metadata)
    cq = _import_cadquery()

    item = BenchmarkItem(root_dir=Path(output_dir), metadata=metadata)
    item.root_dir.mkdir(parents=True, exist_ok=True)

    save_metadata(metadata, item.metadata_path)
    part = build_mounting_plate(metadata)
    cq.exporters.export(part, str(item.target_step_path))
    cq.exporters.export(part, str(item.target_stl_path))

    return item


def generate_mounting_plate(metadata: PartMetadata, output_dir: Path | str) -> BenchmarkItem:
    """Compatibility wrapper for the milestone's generation operation."""

    return export_mounting_plate(metadata, output_dir)


def _validate_mounting_plate_metadata(metadata: PartMetadata) -> None:
    if metadata.family != "mounting_plate":
        raise ValueError(f"Unsupported part family: {metadata.family}")
    if metadata.units != "mm":
        raise ValueError(f"Unsupported units: {metadata.units}")
    if metadata.features.slots:
        raise ValueError("Mounting plate MVP supports through holes only, not slots.")

    dimensions = metadata.dimensions
    for index, hole in enumerate(metadata.features.holes):
        if not hole.through:
            raise ValueError(f"Hole {index} must be a through hole.")

        radius = hole.diameter / 2.0
        x, y = hole.center
        if x - radius < 0 or x + radius > dimensions.length:
            raise ValueError(f"Hole {index} extends beyond the plate length.")
        if y - radius < 0 or y + radius > dimensions.width:
            raise ValueError(f"Hole {index} extends beyond the plate width.")


def _import_cadquery() -> Any:
    try:
        import cadquery as cq
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "CadQuery is required to generate mounting plate CAD artifacts. "
            'Install the optional CAD dependencies with `pip install -e ".[cad]"`.'
        ) from exc
    return cq

"""CadQuery generator for the L-bracket part family."""

from pathlib import Path
from typing import Any

from legacy_part_bench.dataset import BenchmarkItem, PartMetadata, save_metadata

_CUTTER_MARGIN_MM = 1.0


def build_l_bracket(metadata: PartMetadata) -> Any:
    """Build an L-bracket with a base flange, vertical flange, and base holes."""

    _validate_l_bracket_metadata(metadata)
    cq = _import_cadquery()

    dimensions = metadata.dimensions
    flange_thickness = _float_parameter(metadata, "flange_thickness")

    base = cq.Workplane("XY").box(
        dimensions.length,
        dimensions.width,
        flange_thickness,
        centered=(False, False, False),
    )
    vertical = (
        cq.Workplane("XY")
        .box(
            dimensions.length,
            flange_thickness,
            dimensions.thickness,
            centered=(False, False, False),
        )
        .translate((0.0, dimensions.width - flange_thickness, 0.0))
    )
    part = base.union(vertical)

    for hole in metadata.features.holes:
        cutter = (
            cq.Workplane("XY")
            .center(hole.center[0], hole.center[1])
            .circle(hole.diameter / 2.0)
            .extrude(flange_thickness + 2.0 * _CUTTER_MARGIN_MM)
            .translate((0.0, 0.0, -_CUTTER_MARGIN_MM))
        )
        part = part.cut(cutter)

    return part


def export_l_bracket(metadata: PartMetadata, output_dir: Path | str) -> BenchmarkItem:
    """Write metadata and target CAD artifacts for one L-bracket."""

    _validate_l_bracket_metadata(metadata)
    cq = _import_cadquery()

    item = BenchmarkItem(root_dir=Path(output_dir), metadata=metadata)
    item.root_dir.mkdir(parents=True, exist_ok=True)

    save_metadata(metadata, item.metadata_path)
    part = build_l_bracket(metadata)
    cq.exporters.export(part, str(item.target_step_path))
    cq.exporters.export(part, str(item.target_stl_path))

    return item


def _validate_l_bracket_metadata(metadata: PartMetadata) -> None:
    if metadata.family != "l_bracket":
        raise ValueError(f"Unsupported part family: {metadata.family}")
    if metadata.units != "mm":
        raise ValueError(f"Unsupported units: {metadata.units}")
    if metadata.features.slots or metadata.features.steps:
        raise ValueError("L-brackets support base through-holes only in Phase 8.")

    dimensions = metadata.dimensions
    flange_thickness = _float_parameter(metadata, "flange_thickness")
    if flange_thickness <= 0:
        raise ValueError("flange_thickness must be positive.")
    if flange_thickness >= dimensions.width:
        raise ValueError("flange_thickness must be smaller than the bracket width.")
    if flange_thickness >= dimensions.thickness:
        raise ValueError("flange_thickness must be smaller than the bracket height.")

    usable_base_width = dimensions.width - flange_thickness
    for index, hole in enumerate(metadata.features.holes):
        if not hole.through:
            raise ValueError(f"Hole {index} must be a through hole.")
        radius = hole.diameter / 2.0
        x, y = hole.center
        if x - radius < 0 or x + radius > dimensions.length:
            raise ValueError(f"Hole {index} extends beyond the bracket length.")
        if y - radius < 0 or y + radius > usable_base_width:
            raise ValueError(f"Hole {index} must stay on the base flange clear of the vertical flange.")


def _float_parameter(metadata: PartMetadata, name: str) -> float:
    try:
        value = metadata.parameters[name]
    except KeyError as exc:
        raise ValueError(f"Missing L-bracket parameter: {name}") from exc
    if not isinstance(value, (int, float)):
        raise ValueError(f"Parameter {name} must be numeric.")
    return float(value)


def _import_cadquery() -> Any:
    try:
        import cadquery as cq
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "CadQuery is required to generate L-bracket CAD artifacts. "
            'Install the optional CAD dependencies with `pip install -e ".[cad]"`.'
        ) from exc
    return cq

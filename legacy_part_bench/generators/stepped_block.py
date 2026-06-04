"""CadQuery generator for the stepped-block part family."""

from pathlib import Path
from typing import Any

from legacy_part_bench.dataset import BenchmarkItem, PartMetadata, StepFeature, save_metadata


def build_stepped_block(metadata: PartMetadata) -> Any:
    """Build a rectangular stepped block from metadata."""

    _validate_stepped_block_metadata(metadata)
    cq = _import_cadquery()

    dimensions = metadata.dimensions
    base_height = _float_parameter(metadata, "base_height")
    part = cq.Workplane("XY").box(
        dimensions.length,
        dimensions.width,
        base_height,
        centered=(False, False, False),
    )

    for step in metadata.features.steps:
        step_height = step.top_height - base_height
        step_solid = (
            cq.Workplane("XY")
            .box(step.length, dimensions.width, step_height, centered=(False, False, False))
            .translate((step.x_start, 0.0, base_height))
        )
        part = part.union(step_solid)

    return part


def export_stepped_block(metadata: PartMetadata, output_dir: Path | str) -> BenchmarkItem:
    """Write metadata and target CAD artifacts for one stepped block."""

    _validate_stepped_block_metadata(metadata)
    cq = _import_cadquery()

    item = BenchmarkItem(root_dir=Path(output_dir), metadata=metadata)
    item.root_dir.mkdir(parents=True, exist_ok=True)

    save_metadata(metadata, item.metadata_path)
    part = build_stepped_block(metadata)
    cq.exporters.export(part, str(item.target_step_path))
    cq.exporters.export(part, str(item.target_stl_path))

    return item


def _validate_stepped_block_metadata(metadata: PartMetadata) -> None:
    if metadata.family != "stepped_block":
        raise ValueError(f"Unsupported part family: {metadata.family}")
    if metadata.units != "mm":
        raise ValueError(f"Unsupported units: {metadata.units}")
    if metadata.features.holes or metadata.features.slots:
        raise ValueError("Stepped blocks do not support holes or slots in Phase 8.")
    if not metadata.features.steps:
        raise ValueError("Stepped blocks require at least one raised step.")

    dimensions = metadata.dimensions
    base_height = _float_parameter(metadata, "base_height")
    if not 0.0 < base_height < dimensions.thickness:
        raise ValueError("base_height must be between 0 and the overall part height.")

    for index, step in enumerate(metadata.features.steps):
        _validate_step(index, step, metadata)


def _validate_step(index: int, step: StepFeature, metadata: PartMetadata) -> None:
    dimensions = metadata.dimensions
    base_height = _float_parameter(metadata, "base_height")
    if step.x_start + step.length > dimensions.length:
        raise ValueError(f"Step {index} extends beyond the block length.")
    if not base_height < step.top_height <= dimensions.thickness:
        raise ValueError(f"Step {index} top_height must be above base_height and within the part height.")


def _float_parameter(metadata: PartMetadata, name: str) -> float:
    try:
        value = metadata.parameters[name]
    except KeyError as exc:
        raise ValueError(f"Missing stepped-block parameter: {name}") from exc
    if not isinstance(value, (int, float)):
        raise ValueError(f"Parameter {name} must be numeric.")
    return float(value)


def _import_cadquery() -> Any:
    try:
        import cadquery as cq
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "CadQuery is required to generate stepped-block CAD artifacts. "
            'Install the optional CAD dependencies with `pip install -e ".[cad]"`.'
        ) from exc
    return cq

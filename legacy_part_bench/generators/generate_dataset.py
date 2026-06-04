"""Seeded dataset generation for Phase 8 benchmark items."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from legacy_part_bench.dataset import (
    BenchmarkItem,
    HoleFeature,
    PartFamily,
    PartDimensions,
    PartFeatures,
    PartMetadata,
    SlotFeature,
    StepFeature,
)
from legacy_part_bench.generators.drawing_renderer import render_item_drawing
from legacy_part_bench.generators.l_bracket import export_l_bracket
from legacy_part_bench.generators.mounting_plate import export_mounting_plate
from legacy_part_bench.generators.stepped_block import export_stepped_block
from legacy_part_bench.results.run_store import write_benchmark_manifest

LENGTH_RANGE_MM = (60.0, 140.0)
WIDTH_RANGE_MM = (40.0, 100.0)
THICKNESS_RANGE_MM = (4.0, 12.0)
HEIGHT_RANGE_MM = (35.0, 90.0)
HOLE_DIAMETER_RANGE_MM = (4.0, 10.0)
SLOT_WIDTH_RANGE_MM = (5.0, 9.0)
HOLE_COUNTS = (2, 4, 6)
EDGE_CLEARANCE_DIAMETERS = 2.0
MIN_CENTER_DISTANCE_DIAMETERS = 2.5
PART_FAMILIES: tuple[PartFamily, ...] = ("mounting_plate", "stepped_block", "l_bracket")
DIFFICULTY_LEVELS = (1, 2, 3)


@dataclass(frozen=True)
class MountingPlateGenerationConfig:
    """Parameters for one deterministic generation batch."""

    count: int
    seed: int
    output_dir: Path = Path("data/benchmark")
    family: PartFamily = "mounting_plate"
    difficulty: int = 1
    dataset_version: str = "phase8-v1"
    write_manifest: bool = True


def generate_dataset(config: MountingPlateGenerationConfig) -> list[BenchmarkItem]:
    """Generate a deterministic batch of benchmark item folders."""

    if config.family not in PART_FAMILIES:
        raise ValueError(f"Unsupported family: {config.family}")
    if config.difficulty not in DIFFICULTY_LEVELS:
        raise ValueError("difficulty must be 1, 2, or 3")
    if config.count < 1:
        raise ValueError("count must be at least 1")

    rng = random.Random(config.seed)
    items: list[BenchmarkItem] = []
    for index in range(1, config.count + 1):
        metadata = generate_part_metadata(
            index=index,
            rng=rng,
            family=config.family,
            difficulty=config.difficulty,
        )
        item = export_part(metadata, config.output_dir / metadata.id)
        render_item_drawing(item)
        items.append(item)
    if config.write_manifest:
        write_benchmark_manifest(
            config.output_dir,
            dataset_version=config.dataset_version,
            seed=config.seed,
            families=[config.family],
            difficulty_levels=[config.difficulty],
            models=[],
            prompt_mode=None,
            prompt_version=None,
            run_count=0,
            generation_config={
                "count": config.count,
                "family": config.family,
                "difficulty": config.difficulty,
            },
        )
    return items


def generate_part_metadata(
    *,
    index: int,
    rng: random.Random,
    family: PartFamily,
    difficulty: int = 1,
) -> PartMetadata:
    """Generate one valid metadata record for a supported part family."""

    if family == "mounting_plate":
        return generate_mounting_plate_metadata(index=index, rng=rng, difficulty=difficulty)
    if family == "stepped_block":
        return generate_stepped_block_metadata(index=index, rng=rng, difficulty=difficulty)
    if family == "l_bracket":
        return generate_l_bracket_metadata(index=index, rng=rng, difficulty=difficulty)
    raise ValueError(f"Unsupported family: {family}")


def export_part(metadata: PartMetadata, output_dir: Path | str) -> BenchmarkItem:
    """Export one target CAD item for any supported family."""

    if metadata.family == "mounting_plate":
        return export_mounting_plate(metadata, output_dir)
    if metadata.family == "stepped_block":
        return export_stepped_block(metadata, output_dir)
    if metadata.family == "l_bracket":
        return export_l_bracket(metadata, output_dir)
    raise ValueError(f"Unsupported family: {metadata.family}")


def generate_mounting_plate_metadata(
    index: int,
    rng: random.Random,
    difficulty: int = 1,
) -> PartMetadata:
    """Generate one valid mounting-plate metadata record."""

    if index < 1:
        raise ValueError("index must be at least 1")
    if difficulty not in DIFFICULTY_LEVELS:
        raise ValueError("difficulty must be 1, 2, or 3")

    length = _rounded_uniform(rng, *LENGTH_RANGE_MM)
    width = _rounded_uniform(rng, *WIDTH_RANGE_MM)
    thickness = _rounded_uniform(rng, *THICKNESS_RANGE_MM)
    hole_count = _hole_count_for_difficulty(rng, difficulty)
    diameter = _rounded_uniform(rng, HOLE_DIAMETER_RANGE_MM[0], _max_hole_diameter(length, width, hole_count))
    holes = _generate_holes(rng, length=length, width=width, diameter=diameter, hole_count=hole_count)
    slots = _generate_slots(rng, length=length, width=width, difficulty=difficulty, holes=holes)

    return PartMetadata(
        id=f"plate_{index:04d}",
        difficulty=difficulty,
        dimensions=PartDimensions(length=length, width=width, thickness=thickness),
        features=PartFeatures(holes=tuple(holes), slots=tuple(slots)),
    )


def generate_stepped_block_metadata(
    index: int,
    rng: random.Random,
    difficulty: int = 1,
) -> PartMetadata:
    """Generate one valid stepped-block metadata record."""

    if index < 1:
        raise ValueError("index must be at least 1")
    if difficulty not in DIFFICULTY_LEVELS:
        raise ValueError("difficulty must be 1, 2, or 3")

    length = _rounded_uniform(rng, *LENGTH_RANGE_MM)
    width = _rounded_uniform(rng, *WIDTH_RANGE_MM)
    height = _rounded_uniform(rng, 18.0, 45.0)
    base_height = round(height * _rounded_uniform(rng, 0.35, 0.55), 3)

    if difficulty == 1:
        step_length = round(length * _rounded_uniform(rng, 0.42, 0.58), 3)
        x_start = round((length - step_length) / 2.0, 3)
        steps = (StepFeature(x_start=x_start, length=step_length, top_height=height),)
    elif difficulty == 2:
        step_length = round(length * _rounded_uniform(rng, 0.34, 0.52), 3)
        x_start = _rounded_uniform(rng, length * 0.12, length - step_length - length * 0.08)
        steps = (StepFeature(x_start=x_start, length=step_length, top_height=height),)
    else:
        lower_length = round(length * _rounded_uniform(rng, 0.48, 0.62), 3)
        lower_start = round((length - lower_length) / 2.0, 3)
        upper_length = round(lower_length * _rounded_uniform(rng, 0.42, 0.62), 3)
        upper_start = round(lower_start + (lower_length - upper_length) / 2.0, 3)
        lower_top = round(base_height + (height - base_height) * 0.55, 3)
        steps = (
            StepFeature(x_start=lower_start, length=lower_length, top_height=lower_top),
            StepFeature(x_start=upper_start, length=upper_length, top_height=height),
        )

    return PartMetadata(
        id=f"step_{index:04d}",
        family="stepped_block",
        difficulty=difficulty,
        dimensions=PartDimensions(length=length, width=width, thickness=height),
        features=PartFeatures(steps=steps),
        parameters={"base_height": base_height},
    )


def generate_l_bracket_metadata(
    index: int,
    rng: random.Random,
    difficulty: int = 1,
) -> PartMetadata:
    """Generate one valid L-bracket metadata record."""

    if index < 1:
        raise ValueError("index must be at least 1")
    if difficulty not in DIFFICULTY_LEVELS:
        raise ValueError("difficulty must be 1, 2, or 3")

    length = _rounded_uniform(rng, *LENGTH_RANGE_MM)
    width = _rounded_uniform(rng, *WIDTH_RANGE_MM)
    height = _rounded_uniform(rng, *HEIGHT_RANGE_MM)
    flange_thickness = round(min(width, height) * _rounded_uniform(rng, 0.12, 0.20), 3)
    usable_width = width - flange_thickness
    hole_count = 2 if difficulty == 1 else 4
    diameter = _rounded_uniform(
        rng,
        HOLE_DIAMETER_RANGE_MM[0],
        min(HOLE_DIAMETER_RANGE_MM[1], _max_hole_diameter(length, usable_width, hole_count)),
    )
    holes = _generate_holes(
        rng,
        length=length,
        width=usable_width,
        diameter=diameter,
        hole_count=hole_count,
    )

    return PartMetadata(
        id=f"bracket_{index:04d}",
        family="l_bracket",
        difficulty=difficulty,
        dimensions=PartDimensions(length=length, width=width, thickness=height),
        features=PartFeatures(holes=tuple(holes)),
        parameters={"flange_thickness": flange_thickness},
    )


def _generate_holes(
    rng: random.Random,
    *,
    length: float,
    width: float,
    diameter: float,
    hole_count: int,
) -> list[HoleFeature]:
    columns, rows = _hole_grid_shape(hole_count)
    x_positions = _axis_positions(rng, size=length, diameter=diameter, count=columns)
    y_positions = _axis_positions(rng, size=width, diameter=diameter, count=rows)

    return [
        HoleFeature(diameter=diameter, center=(x, y), through=True)
        for y in y_positions
        for x in x_positions
    ]


def _generate_slots(
    rng: random.Random,
    *,
    length: float,
    width: float,
    difficulty: int,
    holes: list[HoleFeature],
) -> list[SlotFeature]:
    if difficulty == 1:
        return []

    row_y_positions = sorted({hole.center[1] for hole in holes})
    if len(row_y_positions) >= 2:
        slot_center_y = round((row_y_positions[0] + row_y_positions[-1]) / 2.0, 3)
        nearest_hole_radius = max(hole.diameter for hole in holes) / 2.0
        clear_half_width = (
            min(abs(slot_center_y - row_y) for row_y in row_y_positions)
            - nearest_hole_radius
            - 1.0
        )
        max_slot_width = max(3.0, clear_half_width * 2.0)
    else:
        slot_center_y = round(width / 2.0, 3)
        max_slot_width = SLOT_WIDTH_RANGE_MM[1]

    slot_width_upper = min(SLOT_WIDTH_RANGE_MM[1], max_slot_width)
    slot_width_lower = min(SLOT_WIDTH_RANGE_MM[0], slot_width_upper)
    slot_width = _rounded_uniform(rng, slot_width_lower, slot_width_upper)
    length_fraction = (0.28, 0.42) if difficulty == 3 else (0.20, 0.34)
    slot_length = _rounded_uniform(
        rng,
        max(slot_width * 2.4, length * length_fraction[0]),
        length * length_fraction[1],
    )
    return [
        SlotFeature(
            length=round(slot_length, 3),
            width=round(slot_width, 3),
            center=(round(length / 2.0, 3), slot_center_y),
            through=True,
            angle_degrees=0.0,
        )
    ]


def _hole_grid_shape(hole_count: int) -> tuple[int, int]:
    if hole_count == 2:
        return 2, 1
    if hole_count == 4:
        return 2, 2
    if hole_count == 6:
        return 3, 2
    raise ValueError(f"Unsupported hole count: {hole_count}")


def _hole_count_for_difficulty(rng: random.Random, difficulty: int) -> int:
    if difficulty == 1:
        return rng.choice((2, 4, 6))
    if difficulty == 2:
        return rng.choice((4, 6))
    return 6


def _axis_positions(rng: random.Random, *, size: float, diameter: float, count: int) -> tuple[float, ...]:
    minimum_edge_clearance = EDGE_CLEARANCE_DIAMETERS * diameter

    if count == 1:
        return (_rounded_uniform(rng, minimum_edge_clearance, size - minimum_edge_clearance),)

    minimum_span = (count - 1) * MIN_CENTER_DISTANCE_DIAMETERS * diameter
    maximum_margin = (size - minimum_span) / 2.0
    if maximum_margin < minimum_edge_clearance:
        raise ValueError("Part is too small for the requested hole layout.")

    margin = _rounded_uniform(rng, minimum_edge_clearance, maximum_margin)
    span = size - 2.0 * margin
    step = span / (count - 1)
    return tuple(round(margin + step * position, 3) for position in range(count))


def _max_hole_diameter(length: float, width: float, hole_count: int) -> float:
    columns, rows = _hole_grid_shape(hole_count)
    max_for_length = length / _diameter_span_factor(columns)
    max_for_width = width / _diameter_span_factor(rows)
    maximum = min(HOLE_DIAMETER_RANGE_MM[1], max_for_length, max_for_width)
    if maximum < HOLE_DIAMETER_RANGE_MM[0]:
        raise ValueError("Generated dimensions cannot fit the minimum hole diameter.")
    return maximum


def _diameter_span_factor(count: int) -> float:
    if count == 1:
        return 2.0 * EDGE_CLEARANCE_DIAMETERS
    return 2.0 * EDGE_CLEARANCE_DIAMETERS + (count - 1) * MIN_CENTER_DISTANCE_DIAMETERS


def _rounded_uniform(rng: random.Random, lower: float, upper: float) -> float:
    return round(rng.uniform(lower, upper), 3)

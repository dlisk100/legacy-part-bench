"""Seeded dataset generation for mounting-plate benchmark items."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from legacy_part_bench.dataset import (
    BenchmarkItem,
    HoleFeature,
    PartDimensions,
    PartFeatures,
    PartMetadata,
)
from legacy_part_bench.generators.drawing_renderer import render_item_drawing
from legacy_part_bench.generators.mounting_plate import export_mounting_plate

LENGTH_RANGE_MM = (60.0, 140.0)
WIDTH_RANGE_MM = (40.0, 100.0)
THICKNESS_RANGE_MM = (4.0, 12.0)
HOLE_DIAMETER_RANGE_MM = (4.0, 10.0)
HOLE_COUNTS = (2, 4, 6)
EDGE_CLEARANCE_DIAMETERS = 2.0
MIN_CENTER_DISTANCE_DIAMETERS = 2.5


@dataclass(frozen=True)
class MountingPlateGenerationConfig:
    """Parameters for one deterministic mounting-plate generation batch."""

    count: int
    seed: int
    output_dir: Path = Path("data/benchmark")
    family: str = "mounting_plate"


def generate_dataset(config: MountingPlateGenerationConfig) -> list[BenchmarkItem]:
    """Generate a deterministic batch of benchmark item folders."""

    if config.family != "mounting_plate":
        raise ValueError(f"Unsupported family: {config.family}")
    if config.count < 1:
        raise ValueError("count must be at least 1")

    rng = random.Random(config.seed)
    items: list[BenchmarkItem] = []
    for index in range(1, config.count + 1):
        metadata = generate_mounting_plate_metadata(index=index, rng=rng)
        item = export_mounting_plate(metadata, config.output_dir / metadata.id)
        render_item_drawing(item)
        items.append(item)
    return items


def generate_mounting_plate_metadata(index: int, rng: random.Random) -> PartMetadata:
    """Generate one valid mounting-plate metadata record."""

    if index < 1:
        raise ValueError("index must be at least 1")

    length = _rounded_uniform(rng, *LENGTH_RANGE_MM)
    width = _rounded_uniform(rng, *WIDTH_RANGE_MM)
    thickness = _rounded_uniform(rng, *THICKNESS_RANGE_MM)
    hole_count = rng.choice(HOLE_COUNTS)
    diameter = _rounded_uniform(rng, HOLE_DIAMETER_RANGE_MM[0], _max_hole_diameter(length, width, hole_count))
    holes = _generate_holes(rng, length=length, width=width, diameter=diameter, hole_count=hole_count)

    return PartMetadata(
        id=f"plate_{index:04d}",
        difficulty=1,
        dimensions=PartDimensions(length=length, width=width, thickness=thickness),
        features=PartFeatures(holes=tuple(holes), slots=()),
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


def _hole_grid_shape(hole_count: int) -> tuple[int, int]:
    if hole_count == 2:
        return 2, 1
    if hole_count == 4:
        return 2, 2
    if hole_count == 6:
        return 3, 2
    raise ValueError(f"Unsupported hole count: {hole_count}")


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

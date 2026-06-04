import importlib.util
import math
import subprocess
import sys

import pytest

from legacy_part_bench.dataset import load_metadata
from legacy_part_bench.generators.generate_dataset import (
    EDGE_CLEARANCE_DIAMETERS,
    HOLE_COUNTS,
    HOLE_DIAMETER_RANGE_MM,
    LENGTH_RANGE_MM,
    MIN_CENTER_DISTANCE_DIAMETERS,
    MountingPlateGenerationConfig,
    THICKNESS_RANGE_MM,
    WIDTH_RANGE_MM,
    generate_dataset,
    generate_l_bracket_metadata,
    generate_mounting_plate_metadata,
    generate_stepped_block_metadata,
)

requires_cadquery = pytest.mark.skipif(
    importlib.util.find_spec("cadquery") is None,
    reason="CadQuery is required for CAD export tests",
)


def metadata_batch(seed: int, count: int = 10) -> list[str]:
    import random

    rng = random.Random(seed)
    return [
        generate_mounting_plate_metadata(index=index, rng=rng).model_dump_json()
        for index in range(1, count + 1)
    ]


def assert_valid_random_mounting_plate(metadata):
    dimensions = metadata.dimensions

    assert LENGTH_RANGE_MM[0] <= dimensions.length <= LENGTH_RANGE_MM[1]
    assert WIDTH_RANGE_MM[0] <= dimensions.width <= WIDTH_RANGE_MM[1]
    assert THICKNESS_RANGE_MM[0] <= dimensions.thickness <= THICKNESS_RANGE_MM[1]
    assert len(metadata.features.holes) in HOLE_COUNTS

    for index, hole in enumerate(metadata.features.holes):
        radius = hole.diameter / 2.0
        edge_clearance = EDGE_CLEARANCE_DIAMETERS * hole.diameter

        assert HOLE_DIAMETER_RANGE_MM[0] <= hole.diameter <= HOLE_DIAMETER_RANGE_MM[1]
        assert hole.through is True
        assert hole.center[0] - radius >= 0
        assert hole.center[0] + radius <= dimensions.length
        assert hole.center[1] - radius >= 0
        assert hole.center[1] + radius <= dimensions.width
        assert hole.center[0] >= edge_clearance
        assert dimensions.length - hole.center[0] >= edge_clearance
        assert hole.center[1] >= edge_clearance
        assert dimensions.width - hole.center[1] >= edge_clearance

        for other in metadata.features.holes[index + 1 :]:
            distance = math.dist(hole.center, other.center)
            assert distance >= MIN_CENTER_DISTANCE_DIAMETERS * hole.diameter


def test_metadata_generation_is_deterministic_by_seed():
    assert metadata_batch(seed=42) == metadata_batch(seed=42)
    assert metadata_batch(seed=42) != metadata_batch(seed=43)


def test_generated_metadata_respects_mounting_plate_ranges_and_spacing():
    import random

    rng = random.Random(42)
    for index in range(1, 31):
        metadata = generate_mounting_plate_metadata(index=index, rng=rng)
        assert metadata.id == f"plate_{index:04d}"
        assert metadata.family == "mounting_plate"
        assert metadata.units == "mm"
        assert_valid_random_mounting_plate(metadata)


@requires_cadquery
def test_generate_dataset_creates_one_valid_folder_per_part(tmp_path):
    items = generate_dataset(MountingPlateGenerationConfig(count=3, seed=42, output_dir=tmp_path))

    assert [item.metadata.id for item in items] == ["plate_0001", "plate_0002", "plate_0003"]
    for item in items:
        assert item.root_dir == tmp_path / item.metadata.id
        assert item.metadata_path.exists()
        assert item.drawing_path.exists()
        assert item.target_step_path.exists()
        assert item.target_stl_path.exists()
        assert item.drawing_path.stat().st_size > 0
        assert item.target_step_path.stat().st_size > 0
        assert item.target_stl_path.stat().st_size > 0
        assert_valid_random_mounting_plate(load_metadata(item.metadata_path))


@requires_cadquery
def test_generate_dataset_cli_acceptance_creates_requested_part_folders(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_dataset.py",
            "--family",
            "mounting_plate",
            "--count",
            "2",
            "--seed",
            "42",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        cwd=".",
        text=True,
        capture_output=True,
    )

    assert "plate_0001" in result.stdout
    assert "plate_0002" in result.stdout
    for part_id in ("plate_0001", "plate_0002"):
        part_dir = tmp_path / part_id
        assert (part_dir / "metadata.json").exists()
        assert (part_dir / "drawing.png").exists()
        assert (part_dir / "target.step").exists()
        assert (part_dir / "target.stl").exists()


def test_phase8_metadata_generation_supports_new_families_and_difficulties():
    import random

    rng = random.Random(7)
    plate = generate_mounting_plate_metadata(index=1, rng=rng, difficulty=3)
    step = generate_stepped_block_metadata(index=1, rng=rng, difficulty=3)
    bracket = generate_l_bracket_metadata(index=1, rng=rng, difficulty=2)

    assert plate.difficulty == 3
    assert len(plate.features.slots) == 1
    assert step.family == "stepped_block"
    assert step.parameters["base_height"] > 0
    assert len(step.features.steps) == 2
    assert bracket.family == "l_bracket"
    assert bracket.parameters["flange_thickness"] > 0
    assert len(bracket.features.holes) == 4


@requires_cadquery
@pytest.mark.parametrize("family,part_prefix", [("stepped_block", "step"), ("l_bracket", "bracket")])
def test_generate_dataset_supports_phase8_families_and_writes_manifest(tmp_path, family, part_prefix):
    items = generate_dataset(
        MountingPlateGenerationConfig(
            family=family,
            count=1,
            seed=42,
            difficulty=2,
            output_dir=tmp_path,
        )
    )

    assert items[0].metadata.id.startswith(f"{part_prefix}_")
    assert items[0].drawing_path.exists()
    assert items[0].target_step_path.exists()
    assert items[0].target_stl_path.exists()
    assert (tmp_path / "manifest.json").exists()

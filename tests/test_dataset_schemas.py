import json

import pytest
from pydantic import ValidationError

from legacy_part_bench.dataset import (
    BenchmarkItem,
    FileReferences,
    HoleFeature,
    PartDimensions,
    PartFeatures,
    PartMetadata,
    SlotFeature,
    StepFeature,
    load_metadata,
    save_metadata,
)


def example_metadata() -> PartMetadata:
    return PartMetadata(
        id="plate_0001",
        difficulty=1,
        dimensions=PartDimensions(length=100.0, width=60.0, thickness=8.0),
        features=PartFeatures(
            holes=(
                HoleFeature(diameter=6.0, center=(20.0, 20.0), through=True),
                HoleFeature(diameter=6.0, center=(80.0, 20.0), through=True),
            ),
            slots=(),
        ),
        files=FileReferences(
            drawing_png="drawing.png",
            target_step="target.step",
            target_stl="target.stl",
        ),
    )


def test_metadata_json_round_trip_preserves_values(tmp_path):
    metadata = example_metadata()
    metadata_path = tmp_path / "plate_0001" / "metadata.json"

    save_metadata(metadata, metadata_path)
    loaded = load_metadata(metadata_path)

    assert loaded == metadata
    assert json.loads(metadata_path.read_text(encoding="utf-8")) == {
        "id": "plate_0001",
        "family": "mounting_plate",
        "units": "mm",
        "difficulty": 1,
        "dimensions": {
            "length": 100.0,
            "width": 60.0,
            "thickness": 8.0,
        },
        "features": {
            "holes": [
                {
                    "diameter": 6.0,
                    "center": [20.0, 20.0],
                    "through": True,
                },
                {
                    "diameter": 6.0,
                    "center": [80.0, 20.0],
                    "through": True,
                },
            ],
            "slots": [],
            "steps": [],
        },
        "parameters": {},
        "files": {
            "drawing_png": "drawing.png",
            "target_step": "target.step",
            "target_stl": "target.stl",
        },
    }


def test_metadata_loads_documented_json_shape(tmp_path):
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "id": "plate_0001",
                "family": "mounting_plate",
                "units": "mm",
                "difficulty": 1,
                "dimensions": {
                    "length": 100.0,
                    "width": 60.0,
                    "thickness": 8.0,
                },
                "features": {
                    "holes": [
                        {
                            "diameter": 6.0,
                            "center": [20.0, 20.0],
                            "through": True,
                        }
                    ],
                    "slots": [],
                },
                "files": {
                    "drawing_png": "drawing.png",
                    "target_step": "target.step",
                    "target_stl": "target.stl",
                },
            }
        ),
        encoding="utf-8",
    )

    metadata = load_metadata(metadata_path)

    assert metadata.id == "plate_0001"
    assert metadata.family == "mounting_plate"
    assert metadata.units == "mm"
    assert metadata.dimensions.length == 100.0
    assert metadata.features.holes[0].center == (20.0, 20.0)


def test_metadata_defaults_to_expected_artifact_filenames():
    metadata = PartMetadata(
        id="plate_0002",
        difficulty=1,
        dimensions=PartDimensions(length=80.0, width=50.0, thickness=6.0),
    )

    assert metadata.files == FileReferences()
    assert metadata.features.holes == ()
    assert metadata.features.slots == ()
    assert metadata.features.steps == ()


def test_phase8_metadata_accepts_slots_steps_parameters_and_new_families():
    plate = PartMetadata(
        id="plate_0003",
        family="mounting_plate",
        difficulty=2,
        dimensions=PartDimensions(length=100.0, width=60.0, thickness=8.0),
        features=PartFeatures(
            slots=(SlotFeature(length=24.0, width=6.0, center=(50.0, 30.0)),),
        ),
    )
    stepped = PartMetadata(
        id="step_0001",
        family="stepped_block",
        difficulty=3,
        dimensions=PartDimensions(length=100.0, width=50.0, thickness=25.0),
        features=PartFeatures(steps=(StepFeature(x_start=25.0, length=50.0, top_height=25.0),)),
        parameters={"base_height": 10.0},
    )
    bracket = PartMetadata(
        id="bracket_0001",
        family="l_bracket",
        difficulty=1,
        dimensions=PartDimensions(length=100.0, width=60.0, thickness=70.0),
        parameters={"flange_thickness": 8.0},
    )

    assert plate.features.slots[0].center == (50.0, 30.0)
    assert stepped.features.steps[0].top_height == 25.0
    assert bracket.parameters["flange_thickness"] == 8.0


def test_benchmark_item_resolves_artifact_paths(tmp_path):
    metadata = example_metadata()
    item = BenchmarkItem(root_dir=tmp_path / "plate_0001", metadata=metadata)

    assert item.metadata_path == tmp_path / "plate_0001" / "metadata.json"
    assert item.drawing_path == tmp_path / "plate_0001" / "drawing.png"
    assert item.target_step_path == tmp_path / "plate_0001" / "target.step"
    assert item.target_stl_path == tmp_path / "plate_0001" / "target.stl"


def test_schema_rejects_invalid_units_and_dimensions():
    with pytest.raises(ValidationError):
        PartMetadata(
            id="plate_0003",
            units="inch",
            difficulty=1,
            dimensions=PartDimensions(length=100.0, width=60.0, thickness=8.0),
        )

    with pytest.raises(ValidationError):
        PartDimensions(length=0.0, width=60.0, thickness=8.0)

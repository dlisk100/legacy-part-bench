import json
import importlib.util

import pytest

from legacy_part_bench.dataset import HoleFeature, PartDimensions, PartFeatures, PartMetadata
from legacy_part_bench.generators.mounting_plate import (
    build_mounting_plate,
    export_mounting_plate,
)

requires_cadquery = pytest.mark.skipif(
    importlib.util.find_spec("cadquery") is None,
    reason="CadQuery is required for CAD export tests",
)


def plate_metadata() -> PartMetadata:
    return PartMetadata(
        id="plate_0001",
        difficulty=1,
        dimensions=PartDimensions(length=100.0, width=60.0, thickness=8.0),
        features=PartFeatures(
            holes=(
                HoleFeature(diameter=6.0, center=(20.0, 20.0), through=True),
                HoleFeature(diameter=6.0, center=(80.0, 40.0), through=True),
            ),
            slots=(),
        ),
    )


@requires_cadquery
def test_build_mounting_plate_matches_metadata_bounding_box():
    part = build_mounting_plate(plate_metadata())

    bounding_box = part.val().BoundingBox()

    assert bounding_box.xmin == pytest.approx(0.0)
    assert bounding_box.ymin == pytest.approx(0.0)
    assert bounding_box.zmin == pytest.approx(0.0)
    assert bounding_box.xlen == pytest.approx(100.0)
    assert bounding_box.ylen == pytest.approx(60.0)
    assert bounding_box.zlen == pytest.approx(8.0)


@requires_cadquery
def test_export_mounting_plate_writes_metadata_and_target_artifacts(tmp_path):
    item = export_mounting_plate(plate_metadata(), tmp_path / "plate_0001")

    assert item.metadata_path.exists()
    assert item.target_step_path.exists()
    assert item.target_stl_path.exists()
    assert item.target_step_path.stat().st_size > 0
    assert item.target_stl_path.stat().st_size > 0
    assert json.loads(item.metadata_path.read_text(encoding="utf-8"))["id"] == "plate_0001"


def test_build_mounting_plate_rejects_non_through_holes():
    metadata = plate_metadata().model_copy(
        update={
            "features": PartFeatures(
                holes=(HoleFeature(diameter=6.0, center=(20.0, 20.0), through=False),),
                slots=(),
            )
        }
    )

    with pytest.raises(ValueError, match="through hole"):
        build_mounting_plate(metadata)


def test_build_mounting_plate_rejects_holes_outside_plate():
    metadata = plate_metadata().model_copy(
        update={
            "features": PartFeatures(
                holes=(HoleFeature(diameter=10.0, center=(2.0, 20.0), through=True),),
                slots=(),
            )
        }
    )

    with pytest.raises(ValueError, match="beyond the plate length"):
        build_mounting_plate(metadata)

import importlib.util

import pytest

from legacy_part_bench.dataset import (
    HoleFeature,
    PartDimensions,
    PartFeatures,
    PartMetadata,
    StepFeature,
)
from legacy_part_bench.generators.l_bracket import build_l_bracket
from legacy_part_bench.generators.stepped_block import build_stepped_block

requires_cadquery = pytest.mark.skipif(
    importlib.util.find_spec("cadquery") is None,
    reason="CadQuery is required for CAD generation tests",
)


@requires_cadquery
def test_build_stepped_block_matches_overall_bounding_box():
    metadata = PartMetadata(
        id="step_0001",
        family="stepped_block",
        difficulty=2,
        dimensions=PartDimensions(length=100.0, width=50.0, thickness=24.0),
        features=PartFeatures(steps=(StepFeature(x_start=25.0, length=50.0, top_height=24.0),)),
        parameters={"base_height": 10.0},
    )

    part = build_stepped_block(metadata)
    bounding_box = part.val().BoundingBox()

    assert bounding_box.xmin == pytest.approx(0.0)
    assert bounding_box.ymin == pytest.approx(0.0)
    assert bounding_box.zmin == pytest.approx(0.0)
    assert bounding_box.xlen == pytest.approx(100.0)
    assert bounding_box.ylen == pytest.approx(50.0)
    assert bounding_box.zlen == pytest.approx(24.0)


@requires_cadquery
def test_build_l_bracket_matches_overall_bounding_box():
    metadata = PartMetadata(
        id="bracket_0001",
        family="l_bracket",
        difficulty=1,
        dimensions=PartDimensions(length=100.0, width=60.0, thickness=70.0),
        features=PartFeatures(
            holes=(HoleFeature(diameter=6.0, center=(25.0, 20.0), through=True),)
        ),
        parameters={"flange_thickness": 8.0},
    )

    part = build_l_bracket(metadata)
    bounding_box = part.val().BoundingBox()

    assert bounding_box.xmin == pytest.approx(0.0)
    assert bounding_box.ymin == pytest.approx(0.0)
    assert bounding_box.zmin == pytest.approx(0.0)
    assert bounding_box.xlen == pytest.approx(100.0)
    assert bounding_box.ylen == pytest.approx(60.0)
    assert bounding_box.zlen == pytest.approx(70.0)


def test_stepped_block_requires_base_height_parameter():
    metadata = PartMetadata(
        id="step_0001",
        family="stepped_block",
        difficulty=1,
        dimensions=PartDimensions(length=100.0, width=50.0, thickness=24.0),
        features=PartFeatures(steps=(StepFeature(x_start=25.0, length=50.0, top_height=24.0),)),
    )

    with pytest.raises(ValueError, match="base_height"):
        build_stepped_block(metadata)


def test_l_bracket_rejects_holes_on_vertical_flange_footprint():
    metadata = PartMetadata(
        id="bracket_0001",
        family="l_bracket",
        difficulty=1,
        dimensions=PartDimensions(length=100.0, width=60.0, thickness=70.0),
        features=PartFeatures(
            holes=(HoleFeature(diameter=6.0, center=(25.0, 56.0), through=True),)
        ),
        parameters={"flange_thickness": 8.0},
    )

    with pytest.raises(ValueError, match="base flange"):
        build_l_bracket(metadata)

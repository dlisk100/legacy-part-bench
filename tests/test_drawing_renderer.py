import importlib.util

import pytest
from PIL import Image

from legacy_part_bench.dataset import (
    HoleFeature,
    PartDimensions,
    PartFeatures,
    PartMetadata,
    SlotFeature,
    StepFeature,
)
from legacy_part_bench.generators.drawing_renderer import (
    dimension_text,
    drawing_notes,
    hole_callout_lines,
    render_l_bracket_drawing,
    render_mounting_plate_drawing,
    render_stepped_block_drawing,
    slot_callout_lines,
    title_block_lines,
)

requires_matplotlib = pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None,
    reason="matplotlib is required for drawing renderer tests",
)


def drawing_metadata(hole_count: int = 2) -> PartMetadata:
    hole_centers = (
        (20.0, 20.0),
        (80.0, 40.0),
        (20.0, 40.0),
        (80.0, 20.0),
        (50.0, 20.0),
        (50.0, 40.0),
    )
    return PartMetadata(
        id="plate_drawing_0001",
        difficulty=1,
        dimensions=PartDimensions(length=100.0, width=60.0, thickness=8.0),
        features=PartFeatures(
            holes=tuple(
                HoleFeature(diameter=6.0, center=center, through=True)
                for center in hole_centers[:hole_count]
            ),
            slots=(),
        ),
    )


def test_title_block_and_notes_include_benchmark_drawing_context():
    title_rows = dict(title_block_lines(drawing_metadata()))
    notes = drawing_notes(drawing_metadata())

    assert title_rows["PART"] == "plate_drawing_0001"
    assert title_rows["UNITS"] == "mm"
    assert title_rows["SCALE"] == "AUTO FIT"
    assert title_rows["PROJECTION"] == "THIRD ANGLE"
    assert "ASME-INSPIRED BENCHMARK DRAWING" in notes
    assert "2X DIA 6 THRU" in notes


@requires_matplotlib
def test_render_mounting_plate_drawing_writes_readable_png(tmp_path):
    output_path = render_mounting_plate_drawing(drawing_metadata(), tmp_path / "drawing.png")

    assert output_path.exists()
    assert output_path.stat().st_size > 0

    image = Image.open(output_path)
    assert image.format == "PNG"
    assert image.width >= 600
    assert image.height >= 400
    assert image.getbbox() is not None


def test_dimension_text_includes_overalls_thickness_and_baseline_hole_locations():
    labels = dimension_text(drawing_metadata())

    assert "LENGTH 100" in labels
    assert "WIDTH 60" in labels
    assert "THICKNESS 8" in labels
    assert "2X DIA 6 THRU" in labels
    assert "H1 X 20" in labels
    assert "H1 Y 20" in labels
    assert "H2 X 80" in labels
    assert "H2 Y 40" in labels


def test_hole_callouts_group_matching_diameters():
    assert hole_callout_lines(drawing_metadata(hole_count=4)) == ["4X DIA 6 THRU"]


def test_slot_callouts_and_dimension_text_include_slot_locations():
    metadata = drawing_metadata().model_copy(
        update={
            "difficulty": 2,
            "features": PartFeatures(
                holes=drawing_metadata().features.holes,
                slots=(SlotFeature(length=24.0, width=8.0, center=(50.0, 30.0)),),
            ),
        }
    )

    assert slot_callout_lines(metadata) == ["1X SLOT 24 X 8 THRU"]
    assert "S1 X 50" in dimension_text(metadata)
    assert "S1 Y 30" in dimension_text(metadata)


@requires_matplotlib
@pytest.mark.parametrize("hole_count", [2, 4, 6])
def test_render_mounting_plate_drawing_supports_mvp_hole_counts(tmp_path, hole_count):
    output_path = render_mounting_plate_drawing(
        drawing_metadata(hole_count=hole_count),
        tmp_path / f"drawing_{hole_count}.png",
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0


@requires_matplotlib
def test_render_mounting_plate_drawing_supports_slots(tmp_path):
    metadata = drawing_metadata().model_copy(
        update={
            "difficulty": 2,
            "features": PartFeatures(
                holes=drawing_metadata().features.holes,
                slots=(SlotFeature(length=24.0, width=8.0, center=(50.0, 30.0)),),
            ),
        }
    )

    output_path = render_mounting_plate_drawing(metadata, tmp_path / "slot_drawing.png")

    assert output_path.exists()
    assert output_path.stat().st_size > 0


@requires_matplotlib
def test_render_stepped_block_and_l_bracket_drawings(tmp_path):
    stepped = PartMetadata(
        id="step_0001",
        family="stepped_block",
        difficulty=2,
        dimensions=PartDimensions(length=100.0, width=50.0, thickness=24.0),
        features=PartFeatures(steps=(StepFeature(x_start=25.0, length=50.0, top_height=24.0),)),
        parameters={"base_height": 10.0},
    )
    bracket = PartMetadata(
        id="bracket_0001",
        family="l_bracket",
        difficulty=1,
        dimensions=PartDimensions(length=100.0, width=60.0, thickness=70.0),
        features=PartFeatures(
            holes=(HoleFeature(diameter=6.0, center=(25.0, 20.0), through=True),)
        ),
        parameters={"flange_thickness": 8.0},
    )

    step_path = render_stepped_block_drawing(stepped, tmp_path / "step.png")
    bracket_path = render_l_bracket_drawing(bracket, tmp_path / "bracket.png")

    assert step_path.exists()
    assert bracket_path.exists()
    assert Image.open(step_path).getbbox() is not None
    assert Image.open(bracket_path).getbbox() is not None

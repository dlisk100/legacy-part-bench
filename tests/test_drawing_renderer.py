import importlib.util

import pytest
from PIL import Image

from legacy_part_bench.dataset import HoleFeature, PartDimensions, PartFeatures, PartMetadata
from legacy_part_bench.generators.drawing_renderer import (
    dimension_text,
    drawing_notes,
    hole_callout_lines,
    render_mounting_plate_drawing,
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


@requires_matplotlib
@pytest.mark.parametrize("hole_count", [2, 4, 6])
def test_render_mounting_plate_drawing_supports_mvp_hole_counts(tmp_path, hole_count):
    output_path = render_mounting_plate_drawing(
        drawing_metadata(hole_count=hole_count),
        tmp_path / f"drawing_{hole_count}.png",
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0

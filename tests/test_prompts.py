import json

import pytest

from legacy_part_bench.dataset import (
    BenchmarkItem,
    HoleFeature,
    PartDimensions,
    PartFeatures,
    PartMetadata,
)
from legacy_part_bench.models import PROMPT_MODES, render_prompt, render_prompt_for_item


def example_metadata() -> PartMetadata:
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


@pytest.mark.parametrize("mode", PROMPT_MODES)
def test_all_prompt_modes_render_required_contract(mode, tmp_path):
    image_path = tmp_path / "drawing.png" if mode != "text_spec_v1" else None

    prompt = render_prompt(mode, metadata=example_metadata(), image_path=image_path)

    assert prompt.mode == mode
    assert "CadQuery" in prompt.text
    assert "millimeters" in prompt.text
    assert "(0, 0, 0)" in prompt.text
    assert "Length runs along +X" in prompt.text
    assert "Width runs along +Y" in prompt.text
    assert "Thickness/height runs along +Z" in prompt.text
    assert "result" in prompt.text
    assert "Return only Python code" in prompt.text


def test_text_spec_prompt_includes_structured_metadata_and_no_image_path():
    prompt = render_prompt("text_spec_v1", metadata=example_metadata())

    assert prompt.image_path is None
    assert '"id": "plate_0001"' in prompt.text
    assert '"family": "mounting_plate"' in prompt.text
    assert '"length": 100.0' in prompt.text
    assert "{{ structured_spec }}" not in prompt.text


def test_image_plus_spec_prompt_includes_structured_metadata_and_image_path(tmp_path):
    image_path = tmp_path / "drawing.png"

    prompt = render_prompt(
        "image_plus_spec_v1",
        metadata=example_metadata(),
        image_path=image_path,
    )

    assert prompt.image_path == image_path
    assert '"holes"' in prompt.text
    assert '"diameter": 6.0' in prompt.text


def test_image_only_prompt_requires_image_but_omits_structured_metadata(tmp_path):
    image_path = tmp_path / "drawing.png"

    prompt = render_prompt("image_only_v1", metadata=example_metadata(), image_path=image_path)

    assert prompt.image_path == image_path
    assert "dimensioned mechanical drawing image" in prompt.text
    assert '"id": "plate_0001"' not in prompt.text
    assert "{{ structured_spec }}" not in prompt.text


def test_image_prompt_modes_require_image_path():
    with pytest.raises(ValueError, match="requires an image_path"):
        render_prompt("image_plus_spec_v1", metadata=example_metadata())

    with pytest.raises(ValueError, match="requires an image_path"):
        render_prompt("image_only_v1", metadata=example_metadata())


def test_unsupported_prompt_mode_fails_clearly():
    with pytest.raises(ValueError, match="Unsupported prompt mode"):
        render_prompt("not_a_mode", metadata=example_metadata())  # type: ignore[arg-type]


def test_render_prompt_for_item_uses_item_drawing_path(tmp_path):
    metadata = example_metadata()
    item = BenchmarkItem(root_dir=tmp_path / metadata.id, metadata=metadata)

    prompt = render_prompt_for_item("image_plus_spec_v1", item)

    assert prompt.image_path == item.drawing_path


def test_structured_spec_is_valid_json():
    prompt = render_prompt("text_spec_v1", metadata=example_metadata())
    json_start = prompt.text.index("{")
    parsed = json.loads(prompt.text[json_start:])

    assert parsed["id"] == "plate_0001"
    assert parsed["features"]["holes"][0]["center"] == [20.0, 20.0]

"""Prompt rendering helpers for model CAD reconstruction runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from legacy_part_bench.dataset import BenchmarkItem, PartMetadata

PromptMode = Literal["text_spec_v1", "image_plus_spec_v1", "image_only_v1"]

PROMPT_MODES: tuple[PromptMode, ...] = (
    "text_spec_v1",
    "image_plus_spec_v1",
    "image_only_v1",
)

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


@dataclass(frozen=True)
class RenderedPrompt:
    """Rendered prompt text plus optional drawing image reference."""

    mode: PromptMode
    text: str
    image_path: Path | None = None


def render_prompt(
    mode: PromptMode,
    *,
    metadata: PartMetadata,
    image_path: Path | str | None = None,
) -> RenderedPrompt:
    """Render one prompt mode from part metadata and optional drawing path."""

    if mode not in PROMPT_MODES:
        raise ValueError(f"Unsupported prompt mode: {mode}")

    resolved_image_path = Path(image_path) if image_path is not None else None
    if mode in {"image_plus_spec_v1", "image_only_v1"} and resolved_image_path is None:
        raise ValueError(f"{mode} requires an image_path.")

    template = _load_template(mode)
    text = template.replace("{{ structured_spec }}", structured_spec_from_metadata(metadata))
    return RenderedPrompt(mode=mode, text=text, image_path=resolved_image_path)


def render_prompt_for_item(mode: PromptMode, item: BenchmarkItem) -> RenderedPrompt:
    """Render a prompt for a benchmark item using its drawing path when needed."""

    image_path = item.drawing_path if mode in {"image_plus_spec_v1", "image_only_v1"} else None
    return render_prompt(mode, metadata=item.metadata, image_path=image_path)


def structured_spec_from_metadata(metadata: PartMetadata) -> str:
    """Return a stable JSON part specification for prompt templates."""

    return json.dumps(metadata.model_dump(mode="json"), indent=2, sort_keys=True)


def _load_template(mode: PromptMode) -> str:
    return (_PROMPT_DIR / f"{mode}.txt").read_text(encoding="utf-8")

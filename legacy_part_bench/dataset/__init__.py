"""Dataset schemas and IO helpers."""

from legacy_part_bench.dataset.io import load_metadata, save_metadata
from legacy_part_bench.dataset.schemas import (
    BenchmarkItem,
    FileReferences,
    HoleFeature,
    ParameterValue,
    PartFamily,
    PartDimensions,
    PartFeatures,
    PartMetadata,
    SlotFeature,
    StepFeature,
)

__all__ = [
    "BenchmarkItem",
    "FileReferences",
    "HoleFeature",
    "ParameterValue",
    "PartFamily",
    "PartDimensions",
    "PartFeatures",
    "PartMetadata",
    "SlotFeature",
    "StepFeature",
    "load_metadata",
    "save_metadata",
]

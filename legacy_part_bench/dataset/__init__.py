"""Dataset schemas and IO helpers."""

from legacy_part_bench.dataset.io import load_metadata, save_metadata
from legacy_part_bench.dataset.schemas import (
    BenchmarkItem,
    FileReferences,
    HoleFeature,
    PartDimensions,
    PartFeatures,
    PartMetadata,
    SlotFeature,
)

__all__ = [
    "BenchmarkItem",
    "FileReferences",
    "HoleFeature",
    "PartDimensions",
    "PartFeatures",
    "PartMetadata",
    "SlotFeature",
    "load_metadata",
    "save_metadata",
]

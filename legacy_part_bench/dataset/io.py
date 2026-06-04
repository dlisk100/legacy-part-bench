"""JSON IO helpers for benchmark dataset metadata."""

from pathlib import Path

from legacy_part_bench.dataset.schemas import PartMetadata


def save_metadata(metadata: PartMetadata, path: Path | str) -> None:
    """Save part metadata as formatted JSON."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(metadata.model_dump_json(indent=2) + "\n", encoding="utf-8")


def load_metadata(path: Path | str) -> PartMetadata:
    """Load part metadata from JSON."""

    input_path = Path(path)
    return PartMetadata.model_validate_json(input_path.read_text(encoding="utf-8"))

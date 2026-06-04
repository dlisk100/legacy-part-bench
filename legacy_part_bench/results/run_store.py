"""File-based run storage helpers for summaries, manifests, and usage."""

from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST_FILENAME = "manifest.json"
SUMMARY_CSV_FILENAME = "summary.csv"
SUMMARY_JSON_FILENAME = "summary.json"
USAGE_FILENAME = "usage.json"


def safe_model_slug(model: str) -> str:
    """Return a filesystem-safe slug for a model id."""

    slug = re.sub(r"[^A-Za-z0-9_.-]+", "__", model.strip())
    return slug.strip("._-") or "unknown_model"


def normalize_provider_usage(raw_json: dict[str, Any] | None) -> dict[str, Any]:
    """Extract token and cost usage from an OpenRouter response."""

    raw_json = raw_json or {}
    usage = raw_json.get("usage")
    if not isinstance(usage, dict):
        usage = {}

    return {
        "generation_id": raw_json.get("id"),
        "model": raw_json.get("model"),
        "prompt_tokens": _optional_int(usage.get("prompt_tokens")),
        "completion_tokens": _optional_int(usage.get("completion_tokens")),
        "total_tokens": _optional_int(usage.get("total_tokens")),
        "cost": _optional_float(usage.get("cost")),
        "is_byok": usage.get("is_byok") if isinstance(usage.get("is_byok"), bool) else None,
        "prompt_tokens_details": usage.get("prompt_tokens_details")
        if isinstance(usage.get("prompt_tokens_details"), dict)
        else None,
        "completion_tokens_details": usage.get("completion_tokens_details")
        if isinstance(usage.get("completion_tokens_details"), dict)
        else None,
        "cost_details": usage.get("cost_details") if isinstance(usage.get("cost_details"), dict) else None,
    }


def write_usage(usage: dict[str, Any], run_dir: Path | str) -> Path:
    """Write normalized provider usage for a run."""

    path = Path(run_dir)
    path.mkdir(parents=True, exist_ok=True)
    usage_path = path / USAGE_FILENAME
    usage_path.write_text(json.dumps(usage, indent=2) + "\n", encoding="utf-8")
    return usage_path


def read_usage(run_dir: Path | str) -> dict[str, Any]:
    """Read normalized provider usage when present."""

    usage_path = Path(run_dir) / USAGE_FILENAME
    if not usage_path.exists():
        return {}
    return json.loads(usage_path.read_text(encoding="utf-8"))


def scorecard_summary_row(
    *,
    run_dir: Path | str,
    scorecard: dict[str, Any],
    run_config: dict[str, Any],
    usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Flatten one scorecard into a batch-summary row."""

    usage = usage or {}
    categories = scorecard.get("categories", {})
    row: dict[str, Any] = {
        "part_id": run_config.get("part_id"),
        "family": run_config.get("family"),
        "difficulty": run_config.get("difficulty"),
        "model": run_config.get("model"),
        "prompt_mode": run_config.get("prompt_mode"),
        "run_dir": str(run_dir),
        "total_score": scorecard.get("total_score", 0.0),
        "passed": scorecard.get("passed", False),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "cost": usage.get("cost"),
    }
    for category_name, category in categories.items():
        if isinstance(category, dict):
            row[f"{category_name}_score"] = category.get("score", 0.0)
    return row


def write_summary(rows: list[dict[str, Any]], output_dir: Path | str) -> tuple[Path, Path]:
    """Write ``summary.csv`` and ``summary.json`` for a batch run."""

    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    json_path = path / SUMMARY_JSON_FILENAME
    csv_path = path / SUMMARY_CSV_FILENAME
    json_path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    fieldnames = _summary_fieldnames(rows)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return csv_path, json_path


def write_benchmark_manifest(
    output_dir: Path | str,
    *,
    dataset_version: str,
    seed: int | None,
    families: list[str],
    difficulty_levels: list[int],
    models: list[str],
    prompt_mode: str | None,
    prompt_version: str | None,
    run_count: int,
    generation_config: dict[str, Any] | None = None,
) -> Path:
    """Write a reproducibility manifest for generated datasets or batch results."""

    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset_version": dataset_version,
        "seed": seed,
        "families": families,
        "difficulty_levels": difficulty_levels,
        "models": models,
        "prompt_mode": prompt_mode,
        "prompt_version": prompt_version,
        "run_count": run_count,
        "generation_config": generation_config or {},
        "created_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": current_git_commit(Path.cwd()),
    }
    manifest_path = path / MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def current_git_commit(cwd: Path | str) -> str | None:
    """Return the current git commit SHA if available."""

    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _summary_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    preferred = [
        "part_id",
        "family",
        "difficulty",
        "model",
        "prompt_mode",
        "total_score",
        "passed",
        "execution_score",
        "export_score",
        "bbox_score",
        "volume_score",
        "features_score",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "cost",
        "run_dir",
    ]
    keys = {key for row in rows for key in row}
    ordered = [key for key in preferred if key in keys]
    ordered.extend(sorted(keys - set(ordered)))
    return ordered


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None

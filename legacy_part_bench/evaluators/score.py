"""Scorecard aggregation for LegacyPartBench generated CAD runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from legacy_part_bench.dataset import BenchmarkItem, PartMetadata, load_metadata
from legacy_part_bench.evaluators.bbox_eval import CategoryScore, evaluate_bounding_box
from legacy_part_bench.evaluators.feature_eval import evaluate_features
from legacy_part_bench.evaluators.volume_eval import evaluate_volume
from legacy_part_bench.sandbox.execute_cadquery import LOG_FILENAME, STL_FILENAME, read_execution_log

SCORECARD_FILENAME = "scorecard.json"
EXECUTION_MAX_SCORE = 20.0
EXPORT_MAX_SCORE = 10.0
BBOX_MAX_SCORE = 20.0
VOLUME_MAX_SCORE = 15.0
FEATURE_MAX_SCORE = 35.0
TOTAL_MAX_SCORE = (
    EXECUTION_MAX_SCORE + EXPORT_MAX_SCORE + BBOX_MAX_SCORE + VOLUME_MAX_SCORE + FEATURE_MAX_SCORE
)


@dataclass(frozen=True)
class Scorecard:
    """Full JSON-serializable benchmark scorecard."""

    total_score: float
    max_score: float
    categories: dict[str, dict[str, Any]]
    passed: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_score": round(self.total_score, 6),
            "max_score": self.max_score,
            "categories": self.categories,
            "passed": self.passed,
            "notes": self.notes,
        }


def score_run(
    *,
    benchmark_item: BenchmarkItem,
    run_dir: Path | str,
    write: bool = True,
) -> Scorecard:
    """Score one generated run directory against a benchmark item."""

    return score_generated_part(
        metadata=benchmark_item.metadata,
        target_stl_path=benchmark_item.target_stl_path,
        generated_stl_path=Path(run_dir) / STL_FILENAME,
        run_dir=run_dir,
        write=write,
    )


def score_generated_part(
    *,
    metadata: PartMetadata,
    target_stl_path: Path | str,
    generated_stl_path: Path | str,
    run_dir: Path | str,
    write: bool = True,
) -> Scorecard:
    """Aggregate execution, export, geometry, and feature scores."""

    resolved_run_dir = Path(run_dir)
    execution_score = _score_execution(resolved_run_dir)
    export_score = _score_export(generated_stl_path)
    notes: list[str] = []

    if execution_score.score <= 0.0:
        notes.append("Execution failed; geometry and feature metrics were skipped.")
        bbox_score = _skipped_category(BBOX_MAX_SCORE, "Execution failed.")
        volume_score = _skipped_category(VOLUME_MAX_SCORE, "Execution failed.")
        feature_score = _skipped_category(FEATURE_MAX_SCORE, "Execution failed.")
    elif export_score.score <= 0.0:
        notes.append("Generated STL export is missing or not loadable; geometry metrics scored zero.")
        bbox_score = _skipped_category(BBOX_MAX_SCORE, "Generated STL export is missing or invalid.")
        volume_score = _skipped_category(VOLUME_MAX_SCORE, "Generated STL export is missing or invalid.")
        feature_score = _skipped_category(FEATURE_MAX_SCORE, "Generated STL export is missing or invalid.")
    else:
        bbox_score = evaluate_bounding_box(
            generated_stl_path,
            metadata,
            max_score=BBOX_MAX_SCORE,
        )
        volume_score = evaluate_volume(
            generated_stl_path,
            target_stl_path,
            max_score=VOLUME_MAX_SCORE,
        )
        feature_score = evaluate_features(
            generated_stl_path,
            metadata,
            max_score=FEATURE_MAX_SCORE,
        )

    categories = {
        "execution": execution_score.to_dict(),
        "export": export_score.to_dict(),
        "bbox": bbox_score.to_dict(),
        "volume": volume_score.to_dict(),
        "features": feature_score.to_dict(),
    }
    total_score = sum(category["score"] for category in categories.values())
    scorecard = Scorecard(
        total_score=total_score,
        max_score=TOTAL_MAX_SCORE,
        categories=categories,
        passed=total_score >= 70.0,
        notes=notes,
    )

    if write:
        write_scorecard(scorecard, resolved_run_dir)
    return scorecard


def score_run_from_paths(
    *,
    benchmark_item_dir: Path | str,
    run_dir: Path | str,
    write: bool = True,
) -> Scorecard:
    """Load metadata from an item folder and score one run directory."""

    item_dir = Path(benchmark_item_dir)
    metadata = load_metadata(item_dir / "metadata.json")
    benchmark_item = BenchmarkItem(root_dir=item_dir, metadata=metadata)
    return score_run(benchmark_item=benchmark_item, run_dir=run_dir, write=write)


def write_scorecard(scorecard: Scorecard, run_dir: Path | str) -> Path:
    """Write ``scorecard.json`` and return its path."""

    path = Path(run_dir)
    path.mkdir(parents=True, exist_ok=True)
    scorecard_path = path / SCORECARD_FILENAME
    scorecard_path.write_text(json.dumps(scorecard.to_dict(), indent=2) + "\n", encoding="utf-8")
    return scorecard_path


def _score_execution(run_dir: Path) -> CategoryScore:
    log = read_execution_log(run_dir)
    if log is None:
        return CategoryScore(
            score=0.0,
            max_score=EXECUTION_MAX_SCORE,
            details={
                "execution_log": str(run_dir / LOG_FILENAME),
                "error": "execution_log.json is missing.",
            },
        )

    return CategoryScore(
        score=EXECUTION_MAX_SCORE if log.success else 0.0,
        max_score=EXECUTION_MAX_SCORE,
        details={
            "success": log.success,
            "status": log.status,
            "duration_seconds": log.duration_seconds,
            "error": log.error,
            "artifacts": log.artifacts,
        },
    )


def _score_export(generated_stl_path: Path | str) -> CategoryScore:
    from legacy_part_bench.evaluators.bbox_eval import load_stl_geometry

    geometry = load_stl_geometry(generated_stl_path)
    score = EXPORT_MAX_SCORE if geometry.loadable and geometry.mesh_valid else 0.0
    return CategoryScore(
        score=score,
        max_score=EXPORT_MAX_SCORE,
        details={"generated_geometry": geometry.to_dict()},
    )


def _skipped_category(max_score: float, reason: str) -> CategoryScore:
    return CategoryScore(score=0.0, max_score=max_score, details={"skipped": True, "reason": reason})

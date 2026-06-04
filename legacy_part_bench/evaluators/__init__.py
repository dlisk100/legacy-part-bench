"""Evaluator helpers for LegacyPartBench scoring."""

from legacy_part_bench.evaluators.bbox_eval import (
    CategoryScore,
    GeometryMetrics,
    evaluate_bounding_box,
    load_stl_geometry,
)
from legacy_part_bench.evaluators.feature_eval import HoleDetection, evaluate_features
from legacy_part_bench.evaluators.score import Scorecard, score_generated_part, score_run, score_run_from_paths
from legacy_part_bench.evaluators.volume_eval import evaluate_volume

__all__ = [
    "CategoryScore",
    "GeometryMetrics",
    "HoleDetection",
    "Scorecard",
    "evaluate_bounding_box",
    "evaluate_features",
    "evaluate_volume",
    "load_stl_geometry",
    "score_generated_part",
    "score_run",
    "score_run_from_paths",
]

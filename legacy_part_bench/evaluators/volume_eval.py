"""Volume similarity evaluator."""

from __future__ import annotations

from pathlib import Path

from legacy_part_bench.evaluators.bbox_eval import CategoryScore, load_stl_geometry


def evaluate_volume(
    generated_stl_path: Path | str,
    target_stl_path: Path | str,
    *,
    max_score: float = 15.0,
    zero_at_relative_error: float = 0.30,
) -> CategoryScore:
    """Score generated STL volume against the target STL volume."""

    generated = load_stl_geometry(generated_stl_path)
    target = load_stl_geometry(target_stl_path)

    if not target.loadable or target.volume is None or target.volume <= 0.0:
        return CategoryScore(
            score=0.0,
            max_score=max_score,
            details={
                "target_geometry": target.to_dict(),
                "generated_geometry": generated.to_dict(),
                "error": target.error or "Target STL has no positive loadable volume.",
            },
        )

    if not generated.loadable or generated.volume is None:
        return CategoryScore(
            score=0.0,
            max_score=max_score,
            details={
                "target_volume": target.volume,
                "generated_geometry": generated.to_dict(),
                "target_geometry": target.to_dict(),
                "error": generated.error or "Generated STL could not be loaded.",
            },
        )

    relative_error = abs(generated.volume - target.volume) / target.volume
    score = max(0.0, 1.0 - relative_error / zero_at_relative_error) * max_score
    return CategoryScore(
        score=score,
        max_score=max_score,
        details={
            "target_volume": target.volume,
            "generated_volume": generated.volume,
            "relative_error": relative_error,
            "target_geometry": target.to_dict(),
            "generated_geometry": generated.to_dict(),
        },
    )

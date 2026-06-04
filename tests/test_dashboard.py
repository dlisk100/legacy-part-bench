from __future__ import annotations

import json
from pathlib import Path

import trimesh

from legacy_part_bench.dashboard.data import (
    discover_runs,
    failure_frame,
    leaderboard_frame,
    runs_to_frame,
)
from legacy_part_bench.dashboard.previews import render_stl_preview


def test_discover_runs_builds_leaderboard_and_failure_tables(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    write_run(
        results_dir / "model_a" / "plate_0001",
        model="model/a",
        part_id="plate_0001",
        total_score=80.0,
        execution_score=20.0,
        execution_success=True,
    )
    write_run(
        results_dir / "model_a" / "plate_0002",
        model="model/a",
        part_id="plate_0002",
        total_score=40.0,
        execution_score=0.0,
        execution_success=False,
    )
    write_run(
        results_dir / "model_b" / "plate_0001",
        model="model/b",
        part_id="plate_0001",
        total_score=90.0,
        execution_score=20.0,
        execution_success=True,
    )

    runs = discover_runs(results_dir)
    frame = runs_to_frame(runs)
    leaderboard = leaderboard_frame(frame)
    failures = failure_frame(frame)

    assert len(runs) == 3
    assert leaderboard["model"].tolist() == ["model/b", "model/a"]
    assert leaderboard.loc[leaderboard["model"] == "model/a", "average_score"].item() == 60.0
    assert leaderboard.loc[leaderboard["model"] == "model/a", "failure_count"].item() == 1
    assert failures["part_id"].tolist() == ["plate_0002"]


def test_local_answer_run_uses_run_type_as_model(tmp_path: Path) -> None:
    run_dir = tmp_path / "results" / "local_test" / "plate_0001"
    write_run(
        run_dir,
        model=None,
        run_type="local_answer",
        part_id="plate_0001",
        total_score=100.0,
        execution_score=20.0,
        execution_success=True,
    )

    frame = runs_to_frame(discover_runs(tmp_path / "results"))

    assert frame.loc[0, "model"] == "local_answer"


def test_render_stl_preview_writes_png_and_reuses_cache(tmp_path: Path) -> None:
    stl_path = tmp_path / "box.stl"
    trimesh.creation.box(extents=(10.0, 6.0, 2.0)).export(stl_path)

    preview_path = render_stl_preview(stl_path)
    second_preview_path = render_stl_preview(stl_path)

    assert preview_path is not None
    assert preview_path == second_preview_path
    assert preview_path.exists()
    assert preview_path.suffix == ".png"
    assert preview_path.stat().st_size > 0


def test_render_stl_preview_returns_none_for_missing_file(tmp_path: Path) -> None:
    assert render_stl_preview(tmp_path / "missing.stl") is None


def write_run(
    run_dir: Path,
    *,
    model: str | None = "model/a",
    run_type: str = "openrouter_model",
    part_id: str,
    total_score: float,
    execution_score: float,
    execution_success: bool,
) -> None:
    run_dir.mkdir(parents=True)
    run_config = {
        "run_type": run_type,
        "part_id": part_id,
        "prompt_mode": "image_plus_spec_v1",
    }
    if model is not None:
        run_config["model"] = model
    scorecard = {
        "total_score": total_score,
        "max_score": 100.0,
        "passed": total_score >= 70.0,
        "categories": {
            "execution": {"score": execution_score, "max_score": 20.0},
            "export": {"score": 10.0 if execution_success else 0.0, "max_score": 10.0},
            "bbox": {"score": 20.0 if execution_success else 0.0, "max_score": 20.0},
            "volume": {"score": 15.0 if execution_success else 0.0, "max_score": 15.0},
            "features": {"score": 35.0 if execution_success else 0.0, "max_score": 35.0},
        },
    }
    execution_log = {"success": execution_success, "status": "success" if execution_success else "error"}
    (run_dir / "run_config.json").write_text(json.dumps(run_config), encoding="utf-8")
    (run_dir / "scorecard.json").write_text(json.dumps(scorecard), encoding="utf-8")
    (run_dir / "execution_log.json").write_text(json.dumps(execution_log), encoding="utf-8")

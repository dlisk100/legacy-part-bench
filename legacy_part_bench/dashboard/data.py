"""Result discovery and aggregation helpers for the Streamlit dashboard."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

SCORECARD_FILENAME = "scorecard.json"
RUN_CONFIG_FILENAME = "run_config.json"
EXECUTION_LOG_FILENAME = "execution_log.json"
RAW_RESPONSE_FILENAME = "raw_response.txt"
EXTRACTED_CODE_FILENAME = "extracted_code.py"
GENERATED_STL_FILENAME = "generated.stl"
TARGET_STL_FILENAME = "target.stl"
DRAWING_FILENAME = "drawing.png"


@dataclass(frozen=True)
class DashboardRun:
    """One run folder plus the parsed artifacts needed by the dashboard."""

    run_dir: Path
    scorecard: dict[str, Any]
    run_config: dict[str, Any]
    execution_log: dict[str, Any] | None

    @property
    def run_id(self) -> str:
        return str(self.run_dir)

    @property
    def part_id(self) -> str:
        return str(
            self.run_config.get("part_id")
            or self.run_dir.name
            or self.scorecard.get("part_id")
            or "unknown_part"
        )

    @property
    def model(self) -> str:
        model = self.run_config.get("model")
        if model:
            return str(model)
        run_type = self.run_config.get("run_type")
        if run_type:
            return str(run_type)
        return "unknown_model"

    @property
    def prompt_mode(self) -> str:
        return str(self.run_config.get("prompt_mode") or "unknown_prompt")

    @property
    def total_score(self) -> float:
        return float(self.scorecard.get("total_score", 0.0))

    @property
    def passed(self) -> bool:
        return bool(self.scorecard.get("passed", False))

    @property
    def part_dir(self) -> Path | None:
        value = self.run_config.get("part_dir")
        return Path(value) if value else None

    @property
    def drawing_path(self) -> Path | None:
        configured = self.run_config.get("image_path")
        if configured:
            path = Path(configured)
            if path.exists():
                return path
        if self.part_dir is not None:
            path = self.part_dir / DRAWING_FILENAME
            if path.exists():
                return path
        return None

    @property
    def target_stl_path(self) -> Path | None:
        if self.part_dir is None:
            return None
        path = self.part_dir / TARGET_STL_FILENAME
        return path if path.exists() else None

    @property
    def generated_stl_path(self) -> Path | None:
        path = self.run_dir / GENERATED_STL_FILENAME
        return path if path.exists() else None

    @property
    def execution_failed(self) -> bool:
        category = self.scorecard.get("categories", {}).get("execution", {})
        if float(category.get("score", 0.0)) <= 0.0:
            return True
        if self.execution_log is not None:
            return not bool(self.execution_log.get("success", False))
        return False


def discover_runs(results_dir: Path | str) -> list[DashboardRun]:
    """Find all run folders under ``results_dir`` that contain a scorecard."""

    root = Path(results_dir)
    if not root.exists():
        return []

    runs: list[DashboardRun] = []
    for scorecard_path in sorted(root.rglob(SCORECARD_FILENAME)):
        run_dir = scorecard_path.parent
        scorecard = _read_json(scorecard_path)
        run_config = _read_json(run_dir / RUN_CONFIG_FILENAME)
        execution_log = _read_optional_json(run_dir / EXECUTION_LOG_FILENAME)
        runs.append(
            DashboardRun(
                run_dir=run_dir,
                scorecard=scorecard,
                run_config=run_config,
                execution_log=execution_log,
            )
        )
    return runs


def runs_to_frame(runs: list[DashboardRun]) -> pd.DataFrame:
    """Convert dashboard runs to a flat table with category score columns."""

    rows: list[dict[str, Any]] = []
    for run in runs:
        categories = run.scorecard.get("categories", {})
        row: dict[str, Any] = {
            "run_id": run.run_id,
            "run_dir": str(run.run_dir),
            "part_id": run.part_id,
            "model": run.model,
            "prompt_mode": run.prompt_mode,
            "total_score": run.total_score,
            "max_score": float(run.scorecard.get("max_score", 100.0)),
            "passed": run.passed,
            "execution_failed": run.execution_failed,
        }
        for category_name, category in categories.items():
            row[f"{category_name}_score"] = float(category.get("score", 0.0))
            row[f"{category_name}_max"] = float(category.get("max_score", 0.0))
        rows.append(row)

    return pd.DataFrame(rows)


def leaderboard_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate average score, category scores, and failures by model."""

    if frame.empty:
        return pd.DataFrame(
            columns=[
                "model",
                "runs",
                "average_score",
                "pass_rate",
                "failure_count",
                "execution",
                "export",
                "bbox",
                "volume",
                "features",
            ]
        )

    grouped = frame.groupby("model", dropna=False)
    leaderboard = grouped.agg(
        runs=("run_id", "count"),
        average_score=("total_score", "mean"),
        pass_rate=("passed", "mean"),
        failure_count=("execution_failed", "sum"),
    )

    for category in ("execution", "export", "bbox", "volume", "features"):
        column = f"{category}_score"
        leaderboard[category] = grouped[column].mean() if column in frame else 0.0

    return leaderboard.reset_index().sort_values(
        ["average_score", "runs"], ascending=[False, False]
    )


def failure_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return runs with execution failures for dashboard display."""

    if frame.empty or "execution_failed" not in frame:
        return pd.DataFrame()
    columns = ["model", "part_id", "prompt_mode", "total_score", "run_dir"]
    return frame.loc[frame["execution_failed"], columns].sort_values(["model", "part_id"])


def read_text_artifact(run: DashboardRun, filename: str) -> str:
    """Read a text artifact from a run folder, returning a clear placeholder."""

    path = run.run_dir / filename
    if not path.exists():
        return f"{filename} is not available for this run."
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_json(path)

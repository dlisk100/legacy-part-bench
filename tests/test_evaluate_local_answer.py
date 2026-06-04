"""Tests for the Phase 5 local end-to-end benchmark script."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from legacy_part_bench.dataset import PartDimensions, PartMetadata, save_metadata

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "evaluate_local_answer.py"

requires_cadquery = pytest.mark.skipif(
    importlib.util.find_spec("cadquery") is None,
    reason="CadQuery is required for successful local end-to-end runs.",
)


@requires_cadquery
def test_evaluate_local_answer_acceptance_example_writes_run_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "local_test" / "plate_0001"

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--part-dir",
            str(REPO_ROOT / "data" / "benchmark" / "plate_0001"),
            "--code-file",
            str(REPO_ROOT / "examples" / "answers" / "plate_0001_good.py"),
            "--output-dir",
            str(run_dir),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert (run_dir / "run_config.json").exists()
    assert (run_dir / "extracted_code.py").exists()
    assert (run_dir / "execution_log.json").exists()
    assert (run_dir / "generated.step").exists()
    assert (run_dir / "generated.stl").exists()
    assert (run_dir / "scorecard.json").exists()

    scorecard = json.loads((run_dir / "scorecard.json").read_text(encoding="utf-8"))
    assert scorecard["total_score"] == pytest.approx(100.0)
    assert scorecard["passed"] is True

    run_config = json.loads((run_dir / "run_config.json").read_text(encoding="utf-8"))
    assert run_config["run_type"] == "local_answer"
    assert run_config["part_id"] == "plate_0001"
    assert run_config["extracted_code_file"] == "extracted_code.py"


def test_evaluate_local_answer_failure_still_writes_log_and_scorecard(tmp_path: Path) -> None:
    part_dir = tmp_path / "benchmark" / "plate_bad"
    part_dir.mkdir(parents=True)
    save_metadata(
        PartMetadata(
            id="plate_bad",
            difficulty=1,
            dimensions=PartDimensions(length=100.0, width=60.0, thickness=8.0),
        ),
        part_dir / "metadata.json",
    )
    answer_path = tmp_path / "missing_result.py"
    answer_path.write_text("x = 1\n", encoding="utf-8")
    run_dir = tmp_path / "results" / "plate_bad"

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--part-dir",
            str(part_dir),
            "--code-file",
            str(answer_path),
            "--output-dir",
            str(run_dir),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert (run_dir / "run_config.json").exists()
    assert (run_dir / "extracted_code.py").read_text(encoding="utf-8") == "x = 1\n"

    execution_log = json.loads((run_dir / "execution_log.json").read_text(encoding="utf-8"))
    assert execution_log["success"] is False
    assert execution_log["status"] == "missing_result"

    scorecard = json.loads((run_dir / "scorecard.json").read_text(encoding="utf-8"))
    assert scorecard["total_score"] == 0.0
    assert scorecard["categories"]["bbox"]["details"]["skipped"] is True

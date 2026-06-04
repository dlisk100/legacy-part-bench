#!/usr/bin/env python
"""Execute and score a local CadQuery answer against one benchmark item."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from legacy_part_bench.dataset import load_metadata
from legacy_part_bench.evaluators import score_run_from_paths
from legacy_part_bench.sandbox.execute_cadquery import execute_cadquery_file

EXTRACTED_CODE_FILENAME = "extracted_code.py"
RUN_CONFIG_FILENAME = "run_config.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item-dir", "--part-dir", dest="item_dir", required=True, type=Path)
    parser.add_argument(
        "--run-dir",
        "--output-dir",
        dest="run_dir",
        required=True,
        type=Path,
        help="Generated run/output folder.",
    )
    parser.add_argument(
        "--code-file",
        type=Path,
        help="Optional CadQuery answer to execute before scoring.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--no-write", action="store_true", help="Print scorecard without writing it.")
    args = parser.parse_args()

    args.run_dir.mkdir(parents=True, exist_ok=True)

    execution_code_path = args.code_file
    if args.code_file is not None:
        execution_code_path = _stage_local_answer(args.code_file, args.run_dir)
        _write_run_config(
            item_dir=args.item_dir,
            code_file=args.code_file,
            staged_code_file=execution_code_path,
            run_dir=args.run_dir,
            timeout_seconds=args.timeout_seconds,
        )
        execute_cadquery_file(
            execution_code_path,
            args.run_dir,
            timeout_seconds=args.timeout_seconds,
        )

    scorecard = score_run_from_paths(
        benchmark_item_dir=args.item_dir,
        run_dir=args.run_dir,
        write=not args.no_write,
    )
    print(json.dumps(scorecard.to_dict(), indent=2))
    return 0 if scorecard.total_score > 0.0 else 1


def _stage_local_answer(code_file: Path, run_dir: Path) -> Path:
    """Copy the local answer into the run folder under the benchmark artifact name."""

    staged_code_path = run_dir / EXTRACTED_CODE_FILENAME
    shutil.copyfile(code_file, staged_code_path)
    return staged_code_path


def _write_run_config(
    *,
    item_dir: Path,
    code_file: Path,
    staged_code_file: Path,
    run_dir: Path,
    timeout_seconds: float,
) -> Path:
    """Write a compact local-run config for reproducibility."""

    metadata = load_metadata(item_dir / "metadata.json")
    config = {
        "run_type": "local_answer",
        "part_id": metadata.id,
        "family": metadata.family,
        "difficulty": metadata.difficulty,
        "part_dir": str(item_dir.resolve()),
        "parameters": metadata.parameters,
        "source_code_file": str(code_file.resolve()),
        "extracted_code_file": staged_code_file.name,
        "timeout_seconds": timeout_seconds,
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    path = run_dir / RUN_CONFIG_FILENAME
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    raise SystemExit(main())

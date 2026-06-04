#!/usr/bin/env python
"""Execute or score a local generated CAD answer against one benchmark item."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from legacy_part_bench.sandbox.execute_cadquery import execute_cadquery_file
from legacy_part_bench.evaluators import score_run_from_paths


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

    if args.code_file is not None:
        execute_cadquery_file(
            args.code_file,
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


if __name__ == "__main__":
    raise SystemExit(main())

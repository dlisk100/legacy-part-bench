#!/usr/bin/env python
"""Generate deterministic LegacyPartBench dataset items."""

from __future__ import annotations

import argparse
from pathlib import Path

from legacy_part_bench.generators.generate_dataset import (
    DIFFICULTY_LEVELS,
    MountingPlateGenerationConfig,
    PART_FAMILIES,
    generate_dataset,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", default="mounting_plate", choices=PART_FAMILIES)
    parser.add_argument("--difficulty", type=int, choices=DIFFICULTY_LEVELS, default=1)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--dataset-version", default="phase8-v1")
    parser.add_argument("--no-manifest", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    items = generate_dataset(
        MountingPlateGenerationConfig(
            family=args.family,
            count=args.count,
            seed=args.seed,
            output_dir=args.output_dir,
            difficulty=args.difficulty,
            dataset_version=args.dataset_version,
            write_manifest=not args.no_manifest,
        )
    )
    for item in items:
        print(item.root_dir)


if __name__ == "__main__":
    main()

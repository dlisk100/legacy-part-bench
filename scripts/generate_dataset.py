#!/usr/bin/env python
"""Generate deterministic LegacyPartBench dataset items."""

from __future__ import annotations

import argparse
from pathlib import Path

from legacy_part_bench.generators.generate_dataset import (
    MountingPlateGenerationConfig,
    generate_dataset,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", default="mounting_plate", choices=["mounting_plate"])
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmark"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    items = generate_dataset(
        MountingPlateGenerationConfig(
            family=args.family,
            count=args.count,
            seed=args.seed,
            output_dir=args.output_dir,
        )
    )
    for item in items:
        print(item.root_dir)


if __name__ == "__main__":
    main()

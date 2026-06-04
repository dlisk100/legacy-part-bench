#!/usr/bin/env python
"""Run a batch LegacyPartBench benchmark across parts and OpenRouter models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from legacy_part_bench.dataset import BenchmarkItem, load_metadata
from legacy_part_bench.models import PROMPT_MODES, ModelRunConfig, run_model_on_item
from legacy_part_bench.models.run_model import PROMPT_VERSION, RUN_CONFIG_FILENAME
from legacy_part_bench.results.run_store import (
    read_usage,
    safe_model_slug,
    scorecard_summary_row,
    write_benchmark_manifest,
    write_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--prompt-mode", choices=PROMPT_MODES, default="image_plus_spec_v1")
    parser.add_argument("--max-parts", type=int)
    parser.add_argument("--output-dir", type=Path, default=Path("data/results"))
    parser.add_argument("--dataset-version", default="phase8-v1")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--executor", choices=("docker", "local"), default="docker")
    parser.add_argument("--force", action="store_true", help="Bypass cached model responses.")
    parser.add_argument("--env-file", type=Path, help="Optional .env file containing OPENROUTER_API_KEY.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.env_file is not None:
        load_dotenv(args.env_file)
    items = discover_items(args.dataset_dir)
    if args.max_parts is not None:
        items = items[: args.max_parts]
    if not items:
        raise SystemExit(f"No benchmark items found under {args.dataset_dir}")

    rows: list[dict[str, object]] = []
    for item in items:
        for model in args.models:
            run_dir = args.output_dir / safe_model_slug(model) / args.prompt_mode / item.metadata.id
            result = run_model_on_item(
                item_dir=item.root_dir,
                run_dir=run_dir,
                config=ModelRunConfig(
                    model=model,
                    prompt_mode=args.prompt_mode,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    timeout_seconds=args.timeout_seconds,
                    executor=args.executor,
                    force=args.force,
                ),
            )
            run_config = _read_json(run_dir / RUN_CONFIG_FILENAME)
            rows.append(
                scorecard_summary_row(
                    run_dir=run_dir,
                    scorecard=result.scorecard,
                    run_config=run_config,
                    usage=read_usage(run_dir),
                )
            )

    write_summary(rows, args.output_dir)
    write_benchmark_manifest(
        args.output_dir,
        dataset_version=args.dataset_version,
        seed=args.seed,
        families=sorted({item.metadata.family for item in items}),
        difficulty_levels=sorted({item.metadata.difficulty for item in items}),
        models=args.models,
        prompt_mode=args.prompt_mode,
        prompt_version=PROMPT_VERSION,
        run_count=len(rows),
        generation_config={
            "dataset_dir": str(args.dataset_dir.resolve()),
            "max_parts": args.max_parts,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "executor": args.executor,
        },
    )
    print(json.dumps(rows, indent=2))
    return 0


def discover_items(dataset_dir: Path) -> list[BenchmarkItem]:
    """Find benchmark item folders that contain ``metadata.json``."""

    items: list[BenchmarkItem] = []
    for metadata_path in sorted(dataset_dir.glob("*/metadata.json")):
        metadata = load_metadata(metadata_path)
        items.append(BenchmarkItem(root_dir=metadata_path.parent, metadata=metadata))
    return items


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())

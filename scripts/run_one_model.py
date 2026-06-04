#!/usr/bin/env python
"""Run one OpenRouter model on one benchmark item and write benchmark artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from legacy_part_bench.models import PROMPT_MODES, ModelRunConfig, run_model_on_item


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item-dir", "--part-dir", dest="item_dir", required=True, type=Path)
    parser.add_argument("--run-dir", "--output-dir", dest="run_dir", required=True, type=Path)
    parser.add_argument(
        "--model", required=True, help="OpenRouter model id, e.g. openai/gpt-4o-mini."
    )
    parser.add_argument(
        "--prompt-mode",
        choices=PROMPT_MODES,
        default="image_plus_spec_v1",
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument(
        "--executor",
        choices=("docker", "local"),
        default="docker",
        help="Execution backend for generated CAD code. Docker is the default sandbox.",
    )
    parser.add_argument("--force", action="store_true", help="Bypass cached model responses.")
    parser.add_argument("--env-file", type=Path, help="Optional .env file containing OPENROUTER_API_KEY.")
    args = parser.parse_args()

    if args.env_file is not None:
        load_dotenv(args.env_file)

    result = run_model_on_item(
        item_dir=args.item_dir,
        run_dir=args.run_dir,
        config=ModelRunConfig(
            model=args.model,
            prompt_mode=args.prompt_mode,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            timeout_seconds=args.timeout_seconds,
            executor=args.executor,
            force=args.force,
        ),
    )
    print(json.dumps(result.scorecard, indent=2))
    return 0 if result.scorecard["total_score"] > 0.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

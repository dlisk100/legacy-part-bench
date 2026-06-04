"""Configuration helpers for LegacyPartBench."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    openrouter_api_key: str | None
    data_dir: Path
    benchmark_dir: Path
    results_dir: Path
    openrouter_app_name: str
    openrouter_site_url: str | None


def load_settings() -> Settings:
    """Load settings from `.env` and environment variables."""
    load_dotenv()

    data_dir = Path(os.getenv("LPB_DATA_DIR", "data"))
    benchmark_dir = Path(os.getenv("LPB_BENCHMARK_DIR", str(data_dir / "benchmark")))
    results_dir = Path(os.getenv("LPB_RESULTS_DIR", str(data_dir / "results")))

    return Settings(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY") or None,
        data_dir=data_dir,
        benchmark_dir=benchmark_dir,
        results_dir=results_dir,
        openrouter_app_name=os.getenv("OPENROUTER_APP_NAME", "LegacyPartBench"),
        openrouter_site_url=os.getenv("OPENROUTER_SITE_URL") or None,
    )

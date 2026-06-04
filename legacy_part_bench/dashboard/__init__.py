"""Dashboard helpers for LegacyPartBench result inspection."""

from legacy_part_bench.dashboard.data import DashboardRun, discover_runs, leaderboard_frame
from legacy_part_bench.dashboard.previews import render_stl_preview

__all__ = [
    "DashboardRun",
    "discover_runs",
    "leaderboard_frame",
    "render_stl_preview",
]

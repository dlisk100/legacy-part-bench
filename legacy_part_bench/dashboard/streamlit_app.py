"""Streamlit dashboard for LegacyPartBench benchmark results."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from legacy_part_bench.config import load_settings
from legacy_part_bench.dashboard.data import (
    EXTRACTED_CODE_FILENAME,
    RAW_RESPONSE_FILENAME,
    DashboardRun,
    discover_runs,
    failure_frame,
    leaderboard_frame,
    read_text_artifact,
    runs_to_frame,
)
from legacy_part_bench.dashboard.previews import render_run_previews


def main() -> None:
    """Render the Streamlit dashboard."""

    st.set_page_config(page_title="LegacyPartBench", layout="wide")
    st.title("LegacyPartBench")

    settings = load_settings()
    default_results_dir = settings.results_dir
    results_dir = Path(
        st.sidebar.text_input("Results directory", value=str(default_results_dir))
    ).expanduser()
    runs = discover_runs(results_dir)
    frame = runs_to_frame(runs)

    st.sidebar.caption(f"{len(runs)} scored runs found")
    if frame.empty:
        st.info("No scorecards found. Run a local or model benchmark first.")
        st.code(
            "python scripts/evaluate_local_answer.py "
            "--part-dir data/benchmark/plate_0001 "
            "--code-file examples/answers/plate_0001_good.py "
            "--output-dir data/results/local_test/plate_0001",
            language="bash",
        )
        return

    filtered_frame, filtered_runs = _apply_filters(frame, runs)
    _render_leaderboard(filtered_frame)
    _render_failures(filtered_frame)
    _render_per_part_results(filtered_frame)
    _render_part_detail(filtered_runs)


def _apply_filters(
    frame,
    runs: list[DashboardRun],
) -> tuple[object, list[DashboardRun]]:
    models = sorted(frame["model"].dropna().unique().tolist())
    prompt_modes = sorted(frame["prompt_mode"].dropna().unique().tolist())
    selected_models = st.sidebar.multiselect("Models", models, default=models)
    selected_prompt_modes = st.sidebar.multiselect(
        "Prompt modes", prompt_modes, default=prompt_modes
    )

    filtered = frame[
        frame["model"].isin(selected_models) & frame["prompt_mode"].isin(selected_prompt_modes)
    ].copy()
    allowed_run_ids = set(filtered["run_id"].tolist())
    filtered_runs = [run for run in runs if run.run_id in allowed_run_ids]
    return filtered, filtered_runs


def _render_leaderboard(frame) -> None:
    st.header("Leaderboard")
    leaderboard = leaderboard_frame(frame)
    st.dataframe(
        leaderboard,
        width="stretch",
        hide_index=True,
        column_config={
            "average_score": st.column_config.NumberColumn(format="%.2f"),
            "pass_rate": st.column_config.NumberColumn(format="%.2f"),
            "execution": st.column_config.NumberColumn(format="%.2f"),
            "export": st.column_config.NumberColumn(format="%.2f"),
            "bbox": st.column_config.NumberColumn(format="%.2f"),
            "volume": st.column_config.NumberColumn(format="%.2f"),
            "features": st.column_config.NumberColumn(format="%.2f"),
            "total_tokens": st.column_config.NumberColumn(format="%d"),
            "total_cost": st.column_config.NumberColumn(format="%.6f"),
        },
    )


def _render_failures(frame) -> None:
    st.header("Failures")
    failures = failure_frame(frame)
    if failures.empty:
        st.success("No execution failures in the selected runs.")
        return
    st.dataframe(failures, width="stretch", hide_index=True)


def _render_per_part_results(frame) -> None:
    st.header("Per-Part Results")
    columns = [
        column
        for column in (
            "part_id",
            "model",
            "prompt_mode",
            "total_score",
            "passed",
            "execution_score",
            "export_score",
            "bbox_score",
            "volume_score",
            "features_score",
            "total_tokens",
            "cost",
            "run_dir",
        )
        if column in frame
    ]
    st.dataframe(
        frame[columns].sort_values(["part_id", "model", "prompt_mode"]),
        width="stretch",
        hide_index=True,
        column_config={
            "total_score": st.column_config.NumberColumn(format="%.2f"),
            "cost": st.column_config.NumberColumn(format="%.6f"),
        },
    )


def _render_part_detail(runs: list[DashboardRun]) -> None:
    st.header("Part Detail")
    if not runs:
        st.info("No runs match the selected filters.")
        return

    labels = [_run_label(run) for run in runs]
    selected_label = st.selectbox("Run", labels)
    run = runs[labels.index(selected_label)]

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Input Drawing")
        if run.drawing_path is not None:
            st.image(str(run.drawing_path), width="stretch")
        else:
            st.caption("No drawing found for this run.")

    with right:
        st.subheader("Scorecard")
        st.json(run.scorecard)

    st.subheader("STL Previews")
    target_preview, generated_preview = render_run_previews(
        target_stl_path=run.target_stl_path,
        generated_stl_path=run.generated_stl_path,
        cache_dir=run.run_dir.parent / "_previews",
    )
    preview_left, preview_right = st.columns(2)
    with preview_left:
        st.caption("Target")
        if target_preview is not None:
            st.image(str(target_preview), width="stretch")
        else:
            st.info("Target STL preview is unavailable.")
    with preview_right:
        st.caption("Generated")
        if generated_preview is not None:
            st.image(str(generated_preview), width="stretch")
        else:
            st.info("Generated STL preview is unavailable.")

    st.subheader("Artifacts")
    artifact_rows = _artifact_rows(run)
    st.dataframe(artifact_rows, width="stretch", hide_index=True)

    raw_tab, code_tab, log_tab, config_tab = st.tabs(
        ["Raw Response", "Extracted Code", "Execution Log", "Run Config"]
    )
    with raw_tab:
        st.text_area(
            "raw_response.txt",
            read_text_artifact(run, RAW_RESPONSE_FILENAME),
            height=360,
            label_visibility="collapsed",
        )
    with code_tab:
        st.code(read_text_artifact(run, EXTRACTED_CODE_FILENAME), language="python")
    with log_tab:
        st.json(run.execution_log or {})
    with config_tab:
        st.json(run.run_config)


def _artifact_rows(run: DashboardRun) -> list[dict[str, str]]:
    artifact_names = [
        "run_config.json",
        RAW_RESPONSE_FILENAME,
        EXTRACTED_CODE_FILENAME,
        "execution_log.json",
        "scorecard.json",
        "usage.json",
        "generated.step",
        "generated.stl",
    ]
    rows = [
        {
            "artifact": name,
            "path": str(run.run_dir / name),
            "exists": str((run.run_dir / name).exists()),
        }
        for name in artifact_names
    ]
    if run.drawing_path is not None:
        rows.append({"artifact": "drawing.png", "path": str(run.drawing_path), "exists": "True"})
    if run.target_stl_path is not None:
        rows.append({"artifact": "target.stl", "path": str(run.target_stl_path), "exists": "True"})
    return rows


def _run_label(run: DashboardRun) -> str:
    return f"{run.part_id} | {run.model} | {run.prompt_mode} | {run.total_score:.1f}"


if __name__ == "__main__":
    main()

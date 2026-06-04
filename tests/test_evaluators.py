"""Tests for Phase 4 scoring evaluators."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import trimesh

from legacy_part_bench.dataset import HoleFeature, PartDimensions, PartFeatures, PartMetadata, SlotFeature
from legacy_part_bench.evaluators import (
    evaluate_bounding_box,
    evaluate_features,
    evaluate_volume,
    load_stl_geometry,
    score_generated_part,
)
from legacy_part_bench.sandbox.execute_cadquery import ExecutionLog, write_execution_log


def test_load_stl_geometry_reports_missing_file(tmp_path: Path) -> None:
    metrics = load_stl_geometry(tmp_path / "missing.stl")

    assert metrics.exists is False
    assert metrics.loadable is False
    assert metrics.error == "STL file does not exist."


def test_bounding_box_perfect_and_major_mismatch(tmp_path: Path) -> None:
    metadata = _metadata(holes=())
    perfect_stl = _export_box(tmp_path / "perfect.stl", extents=(100.0, 60.0, 8.0))
    mismatch_stl = _export_box(tmp_path / "mismatch.stl", extents=(150.0, 60.0, 8.0))

    perfect = evaluate_bounding_box(perfect_stl, metadata)
    mismatch = evaluate_bounding_box(mismatch_stl, metadata)

    assert perfect.score == pytest.approx(20.0)
    assert mismatch.score < 14.0
    assert mismatch.details["relative_errors"][0] == pytest.approx(0.5)


def test_volume_perfect_and_major_mismatch(tmp_path: Path) -> None:
    target_stl = _export_box(tmp_path / "target.stl", extents=(100.0, 60.0, 8.0))
    perfect_stl = _export_box(tmp_path / "perfect.stl", extents=(100.0, 60.0, 8.0))
    mismatch_stl = _export_box(tmp_path / "mismatch.stl", extents=(100.0, 60.0, 4.0))

    perfect = evaluate_volume(perfect_stl, target_stl)
    mismatch = evaluate_volume(mismatch_stl, target_stl)

    assert perfect.score == pytest.approx(15.0)
    assert mismatch.score == pytest.approx(0.0)
    assert mismatch.details["relative_error"] == pytest.approx(0.5)


def test_feature_eval_distinguishes_correct_partial_and_no_holes(tmp_path: Path) -> None:
    metadata = _metadata(
        holes=(
            HoleFeature(diameter=8.0, center=(25.0, 30.0), through=True),
            HoleFeature(diameter=8.0, center=(75.0, 30.0), through=True),
        )
    )
    correct_stl = _export_hole_wall_mesh(tmp_path / "correct.stl", metadata.features.holes)
    partial_stl = _export_hole_wall_mesh(tmp_path / "partial.stl", metadata.features.holes[:1])
    no_holes_stl = _export_box(tmp_path / "no_holes.stl", extents=(100.0, 60.0, 8.0))

    correct = evaluate_features(correct_stl, metadata)
    partial = evaluate_features(partial_stl, metadata)
    no_holes = evaluate_features(no_holes_stl, metadata)

    assert correct.score == pytest.approx(35.0)
    assert correct.details["detected_expected_holes"] == 2
    assert partial.score == pytest.approx(17.5)
    assert partial.details["detected_expected_holes"] == 1
    assert no_holes.score == pytest.approx(0.0)
    assert no_holes.details["detected_expected_holes"] == 0


def test_feature_eval_scores_slots_and_featureless_parts(tmp_path: Path) -> None:
    slot = SlotFeature(length=28.0, width=8.0, center=(50.0, 30.0), through=True)
    metadata = _metadata(holes=()).model_copy(
        update={
            "difficulty": 2,
            "features": PartFeatures(slots=(slot,)),
        }
    )
    correct_stl = _export_slot_wall_mesh(tmp_path / "slot.stl", (slot,))
    no_slot_stl = _export_box(tmp_path / "no_slot.stl", extents=(100.0, 60.0, 8.0))
    featureless_metadata = PartMetadata(
        id="step_eval",
        family="stepped_block",
        difficulty=1,
        dimensions=PartDimensions(length=100.0, width=60.0, thickness=20.0),
        parameters={"base_height": 8.0},
    )

    correct = evaluate_features(correct_stl, metadata)
    missing = evaluate_features(no_slot_stl, metadata)
    featureless = evaluate_features(no_slot_stl, featureless_metadata)

    assert correct.score == pytest.approx(35.0)
    assert correct.details["detected_expected_slots"] == 1
    assert missing.score == pytest.approx(0.0)
    assert featureless.score == pytest.approx(35.0)
    assert featureless.details["note"] == "No explicit feature checks were required for this part."


def test_scorecard_writes_valid_failure_scorecard(tmp_path: Path) -> None:
    metadata = _metadata(holes=())
    target_stl = _export_box(tmp_path / "target.stl", extents=(100.0, 60.0, 8.0))
    run_dir = tmp_path / "run"
    write_execution_log(
        ExecutionLog(
            success=False,
            status="runtime_error",
            code_path="answer.py",
            output_dir=str(run_dir),
            error="boom",
        ),
        run_dir,
    )

    scorecard = score_generated_part(
        metadata=metadata,
        target_stl_path=target_stl,
        generated_stl_path=run_dir / "generated.stl",
        run_dir=run_dir,
    )

    assert scorecard.total_score == 0.0
    assert scorecard.categories["bbox"]["details"]["skipped"] is True
    written = json.loads((run_dir / "scorecard.json").read_text(encoding="utf-8"))
    assert written["notes"] == ["Execution failed; geometry and feature metrics were skipped."]


def test_scorecard_full_score_for_matching_export(tmp_path: Path) -> None:
    metadata = _metadata(holes=())
    target_stl = _export_box(tmp_path / "target.stl", extents=(100.0, 60.0, 8.0))
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    generated_stl = _export_box(run_dir / "generated.stl", extents=(100.0, 60.0, 8.0))
    (run_dir / "generated.step").write_text("placeholder step\n", encoding="utf-8")
    write_execution_log(
        ExecutionLog(
            success=True,
            status="success",
            code_path="answer.py",
            output_dir=str(run_dir),
            artifacts={
                "generated.step": True,
                "generated.stl": True,
                "execution_log.json": True,
            },
        ),
        run_dir,
    )

    scorecard = score_generated_part(
        metadata=metadata,
        target_stl_path=target_stl,
        generated_stl_path=generated_stl,
        run_dir=run_dir,
    )

    assert scorecard.total_score == pytest.approx(100.0)
    assert scorecard.passed is True


def _metadata(*, holes: tuple[HoleFeature, ...]) -> PartMetadata:
    return PartMetadata(
        id="plate_eval",
        difficulty=1,
        dimensions=PartDimensions(length=100.0, width=60.0, thickness=8.0),
        features=PartFeatures(holes=holes),
    )


def _export_box(path: Path, *, extents: tuple[float, float, float]) -> Path:
    mesh = trimesh.creation.box(extents=extents)
    mesh.export(path)
    return path


def _export_hole_wall_mesh(path: Path, holes: tuple[HoleFeature, ...]) -> Path:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    segments = 24
    for hole in holes:
        start = len(vertices)
        radius = hole.diameter / 2.0
        for z in (0.0, 8.0):
            for index in range(segments):
                angle = 2.0 * np.pi * index / segments
                vertices.append(
                    (
                        hole.center[0] + radius * np.cos(angle),
                        hole.center[1] + radius * np.sin(angle),
                        z,
                    )
                )
        for index in range(segments):
            top_current = start + index
            top_next = start + ((index + 1) % segments)
            bottom_current = start + segments + index
            bottom_next = start + segments + ((index + 1) % segments)
            faces.append((top_current, bottom_current, top_next))
            faces.append((top_next, bottom_current, bottom_next))
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.export(path)
    return path


def _export_slot_wall_mesh(path: Path, slots: tuple[SlotFeature, ...]) -> Path:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    samples = 28
    for slot in slots:
        start = len(vertices)
        radius = slot.width / 2.0
        straight_half_length = (slot.length - slot.width) / 2.0
        perimeter: list[tuple[float, float]] = []
        for x in np.linspace(-straight_half_length, straight_half_length, samples // 2):
            perimeter.append((slot.center[0] + x, slot.center[1] + radius))
        for angle in np.linspace(np.pi / 2.0, -np.pi / 2.0, samples // 2):
            perimeter.append(
                (
                    slot.center[0] + straight_half_length + radius * np.cos(angle),
                    slot.center[1] + radius * np.sin(angle),
                )
            )
        for x in np.linspace(straight_half_length, -straight_half_length, samples // 2):
            perimeter.append((slot.center[0] + x, slot.center[1] - radius))
        for angle in np.linspace(-np.pi / 2.0, np.pi / 2.0, samples // 2):
            perimeter.append(
                (
                    slot.center[0] - straight_half_length + radius * np.cos(angle),
                    slot.center[1] + radius * np.sin(angle),
                )
            )
        for z in (0.0, 8.0):
            for x, y in perimeter:
                vertices.append((x, y, z))
        count = len(perimeter)
        for index in range(count):
            top_current = start + index
            top_next = start + ((index + 1) % count)
            bottom_current = start + count + index
            bottom_next = start + count + ((index + 1) % count)
            faces.append((top_current, bottom_current, top_next))
            faces.append((top_next, bottom_current, bottom_next))
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.export(path)
    return path

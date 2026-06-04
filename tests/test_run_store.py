import json

from legacy_part_bench.results.run_store import (
    safe_model_slug,
    scorecard_summary_row,
    write_benchmark_manifest,
    write_summary,
)


def test_safe_model_slug_preserves_readable_model_identity():
    assert safe_model_slug("openai/gpt-4o-mini") == "openai__gpt-4o-mini"


def test_write_summary_and_manifest(tmp_path):
    row = scorecard_summary_row(
        run_dir=tmp_path / "run",
        scorecard={
            "total_score": 88.0,
            "passed": True,
            "categories": {"execution": {"score": 20.0}},
        },
        run_config={
            "part_id": "plate_0001",
            "family": "mounting_plate",
            "difficulty": 2,
            "model": "test/model",
            "prompt_mode": "image_plus_spec_v1",
        },
        usage={"total_tokens": 18, "cost": 0.00018},
    )

    csv_path, json_path = write_summary([row], tmp_path)
    manifest_path = write_benchmark_manifest(
        tmp_path,
        dataset_version="phase8-v1",
        seed=42,
        families=["mounting_plate"],
        difficulty_levels=[2],
        models=["test/model"],
        prompt_mode="image_plus_spec_v1",
        prompt_version="v1",
        run_count=1,
    )

    assert csv_path.exists()
    assert json_path.exists()
    assert manifest_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8"))[0]["total_score"] == 88.0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["seed"] == 42
    assert manifest["models"] == ["test/model"]

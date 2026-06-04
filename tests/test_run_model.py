from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from legacy_part_bench.dataset import PartDimensions, PartMetadata, save_metadata
from legacy_part_bench.models.openrouter_client import OpenRouterResponse
from legacy_part_bench.models.run_model import ModelRunConfig, build_run_key, run_model_on_item

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_one_model.py"


class FakeClient:
    def __init__(self, content: str = "x = 1\n") -> None:
        self.content = content
        self.calls = 0

    def create_completion(self, **kwargs):
        self.calls += 1
        return OpenRouterResponse(
            content=self.content,
            raw_json={
                "id": "gen-test",
                "model": kwargs["model"],
                "choices": [{"message": {"content": self.content}}],
                "usage": {
                    "prompt_tokens": 11,
                    "completion_tokens": 7,
                    "total_tokens": 18,
                    "cost": 0.00018,
                },
            },
            model=kwargs["model"],
            usage={
                "generation_id": "gen-test",
                "model": kwargs["model"],
                "prompt_tokens": 11,
                "completion_tokens": 7,
                "total_tokens": 18,
                "cost": 0.00018,
                "is_byok": None,
                "prompt_tokens_details": None,
                "completion_tokens_details": None,
                "cost_details": None,
            },
            generation_id="gen-test",
        )


def test_build_run_key_is_stable_and_uses_required_fields():
    key_1 = build_run_key(
        model="model-a",
        part_id="plate_0001",
        prompt_mode="image_plus_spec_v1",
        prompt_version="v1",
        image_hash="abc",
        temperature=0.0,
    )
    key_2 = build_run_key(
        model="model-a",
        part_id="plate_0001",
        prompt_mode="image_plus_spec_v1",
        prompt_version="v1",
        image_hash="abc",
        temperature=0.0,
    )
    key_3 = build_run_key(
        model="model-a",
        part_id="plate_0001",
        prompt_mode="image_plus_spec_v1",
        prompt_version="v1",
        image_hash="different",
        temperature=0.0,
    )

    assert key_1 == key_2
    assert key_1 != key_3
    assert len(key_1) == 64


def test_run_model_on_item_writes_failure_artifacts_and_scorecard(tmp_path):
    part_dir = write_minimal_part(tmp_path)
    run_dir = tmp_path / "results" / "plate_0001"
    client = FakeClient("import cadquery as cq\nx = 1\n")

    result = run_model_on_item(
        item_dir=part_dir,
        run_dir=run_dir,
        config=ModelRunConfig(
            model="test/model",
            prompt_mode="text_spec_v1",
            executor="local",
            timeout_seconds=5,
        ),
        client=client,
    )

    assert client.calls == 1
    assert result.cache_hit is False
    assert (run_dir / "run_config.json").exists()
    run_config = json.loads((run_dir / "run_config.json").read_text(encoding="utf-8"))
    assert run_config["family"] == "mounting_plate"
    assert run_config["difficulty"] == 1
    assert run_config["cache_hit"] is False
    assert run_config["usage"]["total_tokens"] == 18
    assert (run_dir / "raw_response.txt").read_text(encoding="utf-8") == (
        "import cadquery as cq\nx = 1\n"
    )
    usage = json.loads((run_dir / "usage.json").read_text(encoding="utf-8"))
    assert usage["cost"] == 0.00018
    assert (run_dir / "extracted_code.py").read_text(encoding="utf-8") == (
        "import cadquery as cq\nx = 1\n"
    )

    execution_log = json.loads((run_dir / "execution_log.json").read_text(encoding="utf-8"))
    assert execution_log["success"] is False
    assert execution_log["status"] == "missing_result"

    scorecard = json.loads((run_dir / "scorecard.json").read_text(encoding="utf-8"))
    assert scorecard["total_score"] == 0.0
    assert scorecard["categories"]["bbox"]["details"]["skipped"] is True


def test_run_model_on_item_uses_cached_response_without_client_call(tmp_path):
    part_dir = write_minimal_part(tmp_path)
    first_run_dir = tmp_path / "results" / "first"
    second_run_dir = tmp_path / "results" / "second"
    config = ModelRunConfig(model="test/model", prompt_mode="text_spec_v1", executor="local")
    client = FakeClient("import cadquery as cq\nx = 1\n")

    first = run_model_on_item(
        item_dir=part_dir,
        run_dir=first_run_dir,
        config=config,
        client=client,
    )
    assert first.cache_hit is False
    assert client.calls == 1

    second_client = FakeClient("raise = should_not_call\n")
    second = run_model_on_item(
        item_dir=part_dir,
        run_dir=second_run_dir,
        config=config,
        client=second_client,
    )

    assert second.run_key == first.run_key
    assert second.cache_hit is True
    assert second_client.calls == 0
    assert (second_run_dir / "raw_response.txt").read_text(encoding="utf-8") == (
        "import cadquery as cq\nx = 1\n"
    )


def test_run_one_model_cli_fails_clearly_without_api_key(tmp_path, monkeypatch):
    part_dir = write_minimal_part(tmp_path)
    run_dir = tmp_path / "results" / "cli"
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--part-dir",
            str(part_dir),
            "--output-dir",
            str(run_dir),
            "--model",
            "test/model",
            "--prompt-mode",
            "text_spec_v1",
            "--executor",
            "local",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert (run_dir / "run_config.json").exists()
    assert not (run_dir / "raw_response.txt").exists()

    execution_log = json.loads((run_dir / "execution_log.json").read_text(encoding="utf-8"))
    assert execution_log["status"] == "runtime_error"
    assert "OPENROUTER_API_KEY is not set" in execution_log["error"]

    scorecard = json.loads((run_dir / "scorecard.json").read_text(encoding="utf-8"))
    assert scorecard["total_score"] == 0.0


def write_minimal_part(tmp_path: Path) -> Path:
    part_dir = tmp_path / "benchmark" / "plate_0001"
    part_dir.mkdir(parents=True)
    save_metadata(
        PartMetadata(
            id="plate_0001",
            difficulty=1,
            dimensions=PartDimensions(length=100.0, width=60.0, thickness=8.0),
        ),
        part_dir / "metadata.json",
    )
    return part_dir

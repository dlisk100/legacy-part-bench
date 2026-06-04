"""Run one OpenRouter model against one benchmark item."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from legacy_part_bench.dataset import BenchmarkItem, load_metadata
from legacy_part_bench.evaluators import score_run
from legacy_part_bench.models.openrouter_client import OpenRouterClient, OpenRouterError
from legacy_part_bench.models.prompts import PromptMode, render_prompt_for_item
from legacy_part_bench.models.response_parser import parse_model_response
from legacy_part_bench.results.run_store import normalize_provider_usage, write_usage
from legacy_part_bench.sandbox.execute_cadquery import (
    ExecutionLog,
    execute_cadquery_file,
    write_execution_log,
)
from legacy_part_bench.sandbox.sandbox_runner import DockerSandboxConfig, run_in_docker_sandbox

RAW_RESPONSE_FILENAME = "raw_response.txt"
PROVIDER_RESPONSE_FILENAME = "provider_response.json"
EXTRACTED_CODE_FILENAME = "extracted_code.py"
RUN_CONFIG_FILENAME = "run_config.json"
CACHE_DIRNAME = "_cache"
PROMPT_VERSION = "v1"
ExecutorMode = Literal["docker", "local"]


@dataclass(frozen=True)
class ModelRunConfig:
    """Configuration for a single benchmark model run."""

    model: str
    prompt_mode: PromptMode
    prompt_version: str = PROMPT_VERSION
    temperature: float = 0.0
    max_tokens: int | None = None
    timeout_seconds: float = 30.0
    executor: ExecutorMode = "docker"
    force: bool = False


@dataclass(frozen=True)
class ModelRunResult:
    """High-level result for a single model run."""

    run_dir: Path
    run_key: str
    cache_hit: bool
    scorecard: dict[str, Any]


@dataclass(frozen=True)
class CachedModelResponse:
    """A model response loaded from cache or returned by OpenRouter."""

    raw_response: str
    raw_json: dict[str, Any]
    usage: dict[str, Any]
    cache_hit: bool


def run_model_on_item(
    *,
    item_dir: Path | str,
    run_dir: Path | str,
    config: ModelRunConfig,
    client: OpenRouterClient | None = None,
) -> ModelRunResult:
    """Call/cache a model response, execute extracted code, and score the run."""

    item = _load_item(Path(item_dir))
    resolved_run_dir = Path(run_dir)
    resolved_run_dir.mkdir(parents=True, exist_ok=True)

    prompt = render_prompt_for_item(config.prompt_mode, item)
    run_key = build_run_key(
        model=config.model,
        part_id=item.metadata.id,
        prompt_mode=config.prompt_mode,
        prompt_version=config.prompt_version,
        image_hash=file_sha256(prompt.image_path) if prompt.image_path else None,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    _write_run_config(
        run_dir=resolved_run_dir,
        item=item,
        config=config,
        run_key=run_key,
        prompt_text=prompt.text,
        image_path=prompt.image_path,
    )

    cache_dir = resolved_run_dir.parent / CACHE_DIRNAME
    cache_record_path = cache_dir / f"{run_key}.json"
    try:
        model_response = _get_or_create_response(
            cache_record_path=cache_record_path,
            prompt_text=prompt.text,
            image_path=prompt.image_path,
            config=config,
            client=client,
        )
        raw_response = model_response.raw_response
        cache_hit = model_response.cache_hit
        (resolved_run_dir / RAW_RESPONSE_FILENAME).write_text(raw_response, encoding="utf-8")
        write_usage(model_response.usage, resolved_run_dir)
        _update_run_config_with_response_metadata(
            run_dir=resolved_run_dir,
            cache_hit=cache_hit,
            usage=model_response.usage,
            provider_model=model_response.raw_json.get("model"),
            generation_id=model_response.raw_json.get("id"),
        )

        parsed = parse_model_response(raw_response)
        (resolved_run_dir / EXTRACTED_CODE_FILENAME).write_text(parsed.code, encoding="utf-8")

        if config.executor == "docker":
            run_in_docker_sandbox(
                resolved_run_dir / EXTRACTED_CODE_FILENAME,
                resolved_run_dir,
                config=DockerSandboxConfig(timeout_seconds=config.timeout_seconds),
            )
        else:
            execute_cadquery_file(
                resolved_run_dir / EXTRACTED_CODE_FILENAME,
                resolved_run_dir,
                timeout_seconds=config.timeout_seconds,
            )
    except Exception as exc:  # noqa: BLE001 - model-run boundary writes failure artifacts.
        _write_available_provider_failure_artifacts(resolved_run_dir, exc)
        _write_model_failure_log(resolved_run_dir, exc)
        cache_hit = False

    scorecard = score_run(benchmark_item=item, run_dir=resolved_run_dir, write=True)
    return ModelRunResult(
        run_dir=resolved_run_dir,
        run_key=run_key,
        cache_hit=cache_hit,
        scorecard=scorecard.to_dict(),
    )


def build_run_key(
    *,
    model: str,
    part_id: str,
    prompt_mode: str,
    prompt_version: str,
    image_hash: str | None,
    temperature: float,
    max_tokens: int | None = None,
) -> str:
    """Build the deterministic cache key specified for model calls."""

    key_payload = {
        "model": model,
        "part_id": part_id,
        "prompt_mode": prompt_mode,
        "prompt_version": prompt_version,
        "image_hash": image_hash,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    encoded = json.dumps(key_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path | str | None) -> str | None:
    """Return a SHA-256 digest for a file, or ``None`` when no path is provided."""

    if path is None:
        return None
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _get_or_create_response(
    *,
    cache_record_path: Path,
    prompt_text: str,
    image_path: Path | None,
    config: ModelRunConfig,
    client: OpenRouterClient | None,
) -> CachedModelResponse:
    if cache_record_path.exists() and not config.force:
        record = json.loads(cache_record_path.read_text(encoding="utf-8"))
        raw_json = record.get("provider_response") if isinstance(record.get("provider_response"), dict) else {}
        usage = record.get("usage") if isinstance(record.get("usage"), dict) else normalize_provider_usage(raw_json)
        return CachedModelResponse(
            raw_response=str(record["raw_response"]),
            raw_json=raw_json,
            usage=usage,
            cache_hit=True,
        )

    active_client = client or OpenRouterClient.from_env()
    response = active_client.create_completion(
        model=config.model,
        prompt_text=prompt_text,
        image_path=image_path,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    usage = response.usage or normalize_provider_usage(response.raw_json)
    cache_record_path.parent.mkdir(parents=True, exist_ok=True)
    cache_record_path.write_text(
        json.dumps(
            {
                "model": config.model,
                "raw_response": response.content,
                "provider_response": response.raw_json,
                "usage": usage,
                "generation_id": response.generation_id,
                "created_at_utc": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return CachedModelResponse(
        raw_response=response.content,
        raw_json=response.raw_json,
        usage=usage,
        cache_hit=False,
    )


def _load_item(item_dir: Path) -> BenchmarkItem:
    metadata = load_metadata(item_dir / "metadata.json")
    return BenchmarkItem(root_dir=item_dir, metadata=metadata)


def _write_run_config(
    *,
    run_dir: Path,
    item: BenchmarkItem,
    config: ModelRunConfig,
    run_key: str,
    prompt_text: str,
    image_path: Path | None,
) -> None:
    payload = {
        "run_type": "openrouter_model",
        "part_id": item.metadata.id,
        "family": item.metadata.family,
        "difficulty": item.metadata.difficulty,
        "part_dir": str(item.root_dir.resolve()),
        "parameters": item.metadata.parameters,
        "model": config.model,
        "prompt_mode": config.prompt_mode,
        "prompt_version": config.prompt_version,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "timeout_seconds": config.timeout_seconds,
        "executor": config.executor,
        "run_key": run_key,
        "image_path": str(image_path.resolve()) if image_path else None,
        "prompt_text": prompt_text,
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    (run_dir / RUN_CONFIG_FILENAME).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def _update_run_config_with_response_metadata(
    *,
    run_dir: Path,
    cache_hit: bool,
    usage: dict[str, Any],
    provider_model: Any,
    generation_id: Any,
) -> None:
    path = run_dir / RUN_CONFIG_FILENAME
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    payload.update(
        {
            "cache_hit": cache_hit,
            "provider_model": provider_model if isinstance(provider_model, str) else None,
            "generation_id": generation_id if isinstance(generation_id, str) else None,
            "usage": usage,
        }
    )
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_model_failure_log(run_dir: Path, exc: BaseException) -> None:
    log = ExecutionLog(
        success=False,
        status="runtime_error",
        code_path=str(run_dir / EXTRACTED_CODE_FILENAME),
        output_dir=str(run_dir),
        error=_failure_message(exc),
        artifacts={
            "raw_response.txt": (run_dir / RAW_RESPONSE_FILENAME).exists(),
            "provider_response.json": (run_dir / PROVIDER_RESPONSE_FILENAME).exists(),
            "extracted_code.py": (run_dir / EXTRACTED_CODE_FILENAME).exists(),
            "generated.step": (run_dir / "generated.step").exists(),
            "generated.stl": (run_dir / "generated.stl").exists(),
            "execution_log.json": True,
        },
    )
    write_execution_log(log, run_dir)


def _failure_message(exc: BaseException) -> str:
    if isinstance(exc, OpenRouterError):
        return str(exc)
    return f"{type(exc).__name__}: {exc}"


def _write_available_provider_failure_artifacts(run_dir: Path, exc: BaseException) -> None:
    if not isinstance(exc, OpenRouterError) or not isinstance(exc.raw_json, dict):
        return
    raw_json = exc.raw_json
    (run_dir / PROVIDER_RESPONSE_FILENAME).write_text(
        json.dumps(raw_json, indent=2) + "\n",
        encoding="utf-8",
    )
    usage = normalize_provider_usage(raw_json)
    write_usage(usage, run_dir)
    _update_run_config_with_response_metadata(
        run_dir=run_dir,
        cache_hit=False,
        usage=usage,
        provider_model=raw_json.get("model"),
        generation_id=raw_json.get("id"),
    )

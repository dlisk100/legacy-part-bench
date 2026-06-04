"""Docker runner for executing untrusted generated CadQuery code."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from legacy_part_bench.sandbox.execute_cadquery import (
    ExecutionLog,
    ExecutionStatus,
    read_execution_log,
    write_execution_log,
)

DEFAULT_IMAGE_NAME = "legacy-part-bench-cad-sandbox"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MEMORY_LIMIT = "2g"
DEFAULT_CPUS = "1"
DEFAULT_PLATFORM = "linux/amd64"


@dataclass(frozen=True)
class DockerSandboxConfig:
    """Docker execution settings for generated CAD code."""

    image: str = DEFAULT_IMAGE_NAME
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    memory: str = DEFAULT_MEMORY_LIMIT
    cpus: str = DEFAULT_CPUS
    platform: str | None = DEFAULT_PLATFORM
    docker_executable: str = "docker"


def build_sandbox_image(
    *,
    image: str = DEFAULT_IMAGE_NAME,
    dockerfile: Path | str | None = None,
    context_dir: Path | str | None = None,
    platform: str | None = DEFAULT_PLATFORM,
    docker_executable: str = "docker",
) -> subprocess.CompletedProcess[str]:
    """Build the Docker sandbox image."""

    package_root = Path(__file__).resolve().parents[1]
    dockerfile_path = Path(dockerfile) if dockerfile else Path(__file__).with_name("Dockerfile")
    context_path = Path(context_dir) if context_dir else package_root
    command = [docker_executable]
    if platform is None:
        command.append("build")
    else:
        command.extend(["buildx", "build", "--load", "--platform", platform])
    command.extend(["-t", image])
    command.extend(
        [
            "-f",
            str(dockerfile_path),
            str(context_path),
        ]
    )
    return subprocess.run(command, text=True, capture_output=True, check=False)


def run_in_docker_sandbox(
    code_path: Path | str,
    output_dir: Path | str,
    *,
    config: DockerSandboxConfig | None = None,
) -> ExecutionLog:
    """Run generated code in Docker with no network and write execution logs."""

    active_config = config or DockerSandboxConfig()
    resolved_code_path = Path(code_path).resolve()
    resolved_output_dir = Path(output_dir).resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    if shutil.which(active_config.docker_executable) is None:
        log = _runner_failure_log(
            resolved_code_path,
            resolved_output_dir,
            error=f"Docker executable not found: {active_config.docker_executable}",
            status="runtime_error",
        )
        write_execution_log(log, resolved_output_dir)
        return log

    command = docker_run_command(resolved_code_path, resolved_output_dir, active_config)
    started_at = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=active_config.timeout_seconds + 2.0,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        log = _runner_failure_log(
            resolved_code_path,
            resolved_output_dir,
            error=f"Docker sandbox timed out after {active_config.timeout_seconds:g} seconds.",
            status="timeout",
            duration_seconds=round(time.monotonic() - started_at, 6),
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
        )
        write_execution_log(log, resolved_output_dir)
        return log

    log = read_execution_log(resolved_output_dir)
    if log is None:
        log = _runner_failure_log(
            resolved_code_path,
            resolved_output_dir,
            error="Docker sandbox did not write execution_log.json.",
            status="runtime_error",
            duration_seconds=round(time.monotonic() - started_at, 6),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        write_execution_log(log, resolved_output_dir)
        return log

    merged_log = ExecutionLog(
        **{
            **log.to_dict(),
            "returncode": completed.returncode,
            "stdout": _join_streams(log.stdout, completed.stdout),
            "stderr": _join_streams(log.stderr, completed.stderr),
        }
    )
    write_execution_log(merged_log, resolved_output_dir)
    return merged_log


def docker_run_command(
    code_path: Path,
    output_dir: Path,
    config: DockerSandboxConfig,
) -> list[str]:
    """Return the Docker command used for sandbox execution."""

    command = [
        config.docker_executable,
        "run",
        "--rm",
    ]
    if config.platform is not None:
        command.extend(["--platform", config.platform])
    command.extend(
        [
            "--network",
            "none",
            "--cpus",
            config.cpus,
            "--memory",
            config.memory,
            "--mount",
            f"type=bind,src={code_path},dst=/work/input.py,readonly",
            "--mount",
            f"type=bind,src={output_dir},dst=/work/output",
            config.image,
            "--code-file",
            "/work/input.py",
            "--output-dir",
            "/work/output",
            "--timeout-seconds",
            str(config.timeout_seconds),
        ]
    )
    return command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run generated CadQuery code in Docker.")
    parser.add_argument("--code-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--image", default=DEFAULT_IMAGE_NAME)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--memory", default=DEFAULT_MEMORY_LIMIT)
    parser.add_argument("--cpus", default=DEFAULT_CPUS)
    parser.add_argument("--platform", default=DEFAULT_PLATFORM)
    parser.add_argument("--build-image", action="store_true")
    args = parser.parse_args(argv)

    config = DockerSandboxConfig(
        image=args.image,
        timeout_seconds=args.timeout_seconds,
        memory=args.memory,
        cpus=args.cpus,
        platform=args.platform or None,
    )

    if args.build_image:
        build_result = build_sandbox_image(image=args.image, platform=config.platform)
        if build_result.returncode != 0:
            print(build_result.stdout, end="")
            print(build_result.stderr, end="")
            return build_result.returncode

    log = run_in_docker_sandbox(args.code_file, args.output_dir, config=config)
    return 0 if log.success else 1


def _runner_failure_log(
    code_path: Path,
    output_dir: Path,
    *,
    error: str,
    status: ExecutionStatus,
    duration_seconds: float = 0.0,
    returncode: int | None = None,
    stdout: str = "",
    stderr: str = "",
) -> ExecutionLog:
    return ExecutionLog(
        success=False,
        status=status,
        code_path=str(code_path),
        output_dir=str(output_dir),
        duration_seconds=duration_seconds,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        error=error,
        artifacts={
            "generated.step": (output_dir / "generated.step").exists(),
            "generated.stl": (output_dir / "generated.stl").exists(),
            "execution_log.json": True,
        },
    )


def _join_streams(first: str, second: str) -> str:
    if first and second:
        return f"{first}\n{second}"
    return first or second


if __name__ == "__main__":
    raise SystemExit(main())

"""CAD execution sandbox helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from legacy_part_bench.sandbox.execute_cadquery import (
        ExecutionLog,
        execute_cadquery_file,
        execute_cadquery_file_in_process,
        read_execution_log,
        write_execution_log,
    )
    from legacy_part_bench.sandbox.sandbox_runner import (
        DockerSandboxConfig,
        build_sandbox_image,
        run_in_docker_sandbox,
    )

__all__ = [
    "DockerSandboxConfig",
    "ExecutionLog",
    "build_sandbox_image",
    "execute_cadquery_file",
    "execute_cadquery_file_in_process",
    "read_execution_log",
    "run_in_docker_sandbox",
    "write_execution_log",
]


def __getattr__(name: str) -> Any:
    if name in {
        "ExecutionLog",
        "execute_cadquery_file",
        "execute_cadquery_file_in_process",
        "read_execution_log",
        "write_execution_log",
    }:
        from legacy_part_bench.sandbox import execute_cadquery

        return getattr(execute_cadquery, name)

    if name in {
        "DockerSandboxConfig",
        "build_sandbox_image",
        "run_in_docker_sandbox",
    }:
        from legacy_part_bench.sandbox import sandbox_runner

        return getattr(sandbox_runner, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

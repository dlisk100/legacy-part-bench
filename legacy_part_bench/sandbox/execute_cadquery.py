"""Execute one generated CadQuery answer and export generated CAD artifacts."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

ExecutionStatus = Literal[
    "success",
    "syntax_error",
    "missing_result",
    "runtime_error",
    "export_error",
    "timeout",
]

LOG_FILENAME = "execution_log.json"
STEP_FILENAME = "generated.step"
STL_FILENAME = "generated.stl"


@dataclass(frozen=True)
class ExecutionLog:
    """JSON-serializable execution result for generated CAD code."""

    success: bool
    status: ExecutionStatus
    code_path: str
    output_dir: str
    generated_step: str = STEP_FILENAME
    generated_stl: str = STL_FILENAME
    duration_seconds: float = 0.0
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    traceback: str | None = None
    artifacts: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def execute_cadquery_file(
    code_path: Path | str,
    output_dir: Path | str,
    *,
    timeout_seconds: float = 30.0,
    python_executable: Path | str | None = None,
) -> ExecutionLog:
    """Run generated code in a child Python process and return its execution log."""

    resolved_code_path = Path(code_path).resolve()
    resolved_output_dir = Path(output_dir).resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    started_at = time.monotonic()
    command = [
        str(python_executable or sys.executable),
        str(Path(__file__).resolve()),
        "--code-file",
        str(resolved_code_path),
        "--output-dir",
        str(resolved_output_dir),
        "--in-process",
    ]

    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        log = ExecutionLog(
            success=False,
            status="timeout",
            code_path=str(resolved_code_path),
            output_dir=str(resolved_output_dir),
            duration_seconds=round(time.monotonic() - started_at, 6),
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            error=f"Execution timed out after {timeout_seconds:g} seconds.",
            artifacts=_artifact_status(resolved_output_dir, log_will_be_written=True),
        )
        write_execution_log(log, resolved_output_dir)
        return log

    log = read_execution_log(resolved_output_dir)
    if log is None:
        log = ExecutionLog(
            success=False,
            status="runtime_error",
            code_path=str(resolved_code_path),
            output_dir=str(resolved_output_dir),
            duration_seconds=round(time.monotonic() - started_at, 6),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            error="Executor subprocess did not write execution_log.json.",
            artifacts=_artifact_status(resolved_output_dir),
        )
        write_execution_log(log, resolved_output_dir)
        return log

    merged_log = ExecutionLog(
        **{
            **log.to_dict(),
            "returncode": completed.returncode,
            "stdout": _join_streams(log.stdout, completed.stdout),
            "stderr": _join_streams(log.stderr, completed.stderr),
            "artifacts": _artifact_status(resolved_output_dir),
        }
    )
    write_execution_log(merged_log, resolved_output_dir)
    return merged_log


def execute_cadquery_file_in_process(code_path: Path | str, output_dir: Path | str) -> ExecutionLog:
    """Execute generated code in the current process.

    This is used by the child process and Docker container entrypoint. Benchmark
    callers should prefer ``execute_cadquery_file`` or the Docker runner.
    """

    resolved_code_path = Path(code_path).resolve()
    resolved_output_dir = Path(output_dir).resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    started_at = time.monotonic()

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    status: ExecutionStatus = "success"
    error: str | None = None
    traceback_text: str | None = None
    success = False

    with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
        try:
            source = resolved_code_path.read_text(encoding="utf-8")
            compiled = compile(source, str(resolved_code_path), "exec")
            namespace = _execution_namespace()
            exec(compiled, namespace)

            if "result" not in namespace:
                status = "missing_result"
                error = "Generated code did not assign the final CadQuery object to `result`."
            else:
                _export_result(namespace["result"], resolved_output_dir)
                success = True
        except SyntaxError as exc:
            status = "syntax_error"
            error = _format_exception_message(exc)
            traceback_text = traceback.format_exc()
        except _ExportError as exc:
            status = "export_error"
            error = _format_exception_message(exc)
            traceback_text = traceback.format_exc()
        except Exception as exc:  # noqa: BLE001 - this boundary writes structured failure logs.
            if status == "success":
                status = "runtime_error"
            error = _format_exception_message(exc)
            traceback_text = traceback.format_exc()

    log = ExecutionLog(
        success=success,
        status=status,
        code_path=str(resolved_code_path),
        output_dir=str(resolved_output_dir),
        duration_seconds=round(time.monotonic() - started_at, 6),
        stdout=stdout_buffer.getvalue(),
        stderr=stderr_buffer.getvalue(),
        error=error,
        traceback=traceback_text,
        artifacts=_artifact_status(resolved_output_dir),
    )
    write_execution_log(log, resolved_output_dir)
    return log


def write_execution_log(log: ExecutionLog, output_dir: Path | str) -> Path:
    """Write ``execution_log.json`` and return its path."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    log_path = output_path / LOG_FILENAME
    log_path.write_text(json.dumps(log.to_dict(), indent=2) + "\n", encoding="utf-8")
    return log_path


def read_execution_log(output_dir: Path | str) -> ExecutionLog | None:
    """Read ``execution_log.json`` if it exists."""

    log_path = Path(output_dir) / LOG_FILENAME
    if not log_path.exists():
        return None
    return ExecutionLog(**json.loads(log_path.read_text(encoding="utf-8")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute generated CadQuery code.")
    parser.add_argument("--code-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="Run directly in this process. Used inside the child process/container.",
    )
    args = parser.parse_args(argv)

    if args.in_process:
        log = execute_cadquery_file_in_process(args.code_file, args.output_dir)
    else:
        log = execute_cadquery_file(
            args.code_file,
            args.output_dir,
            timeout_seconds=args.timeout_seconds,
        )
    return 0 if log.success else 1


def _execution_namespace() -> dict[str, Any]:
    return {
        "__builtins__": __builtins__,
        "__name__": "__legacy_part_bench_generated_cad__",
        "__file__": "<generated-cad-code>",
    }


def _export_result(result: Any, output_dir: Path) -> None:
    try:
        import cadquery as cq

        cq.exporters.export(result, str(output_dir / STEP_FILENAME))
        cq.exporters.export(result, str(output_dir / STL_FILENAME))
    except Exception as exc:  # noqa: BLE001 - convert exporter failures to structured logs.
        raise _ExportError(_format_exception_message(exc)) from exc


def _artifact_status(output_dir: Path, *, log_will_be_written: bool = False) -> dict[str, bool]:
    return {
        STEP_FILENAME: (output_dir / STEP_FILENAME).exists(),
        STL_FILENAME: (output_dir / STL_FILENAME).exists(),
        LOG_FILENAME: log_will_be_written or (output_dir / LOG_FILENAME).exists(),
    }


def _format_exception_message(exc: BaseException) -> str:
    return f"{exc.__class__.__name__}: {exc}"


def _join_streams(first: str, second: str) -> str:
    if first and second:
        return f"{first}\n{second}"
    return first or second


class _ExportError(RuntimeError):
    pass


if __name__ == "__main__":
    raise SystemExit(main())

import importlib.util
import json
import subprocess
import sys

import pytest

from legacy_part_bench.sandbox import execute_cadquery_file

requires_cadquery = pytest.mark.skipif(
    importlib.util.find_spec("cadquery") is None,
    reason="CadQuery is required for valid CAD export tests",
)


def write_code(tmp_path, source: str):
    code_path = tmp_path / "answer.py"
    code_path.write_text(source, encoding="utf-8")
    return code_path


def read_log(output_dir):
    return json.loads((output_dir / "execution_log.json").read_text(encoding="utf-8"))


@requires_cadquery
def test_execute_cadquery_file_exports_step_stl_and_log_for_valid_code(tmp_path):
    code_path = write_code(
        tmp_path,
        """
import cadquery as cq

result = cq.Workplane("XY").box(100, 60, 8, centered=(False, False, False))
""".strip(),
    )
    output_dir = tmp_path / "run"

    log = execute_cadquery_file(code_path, output_dir, timeout_seconds=10)

    assert log.success is True
    assert log.status == "success"
    assert (output_dir / "generated.step").exists()
    assert (output_dir / "generated.stl").exists()
    assert read_log(output_dir)["success"] is True


def test_execute_cadquery_file_fails_cleanly_for_syntax_error(tmp_path):
    code_path = write_code(tmp_path, "def nope(:\n    pass\n")
    output_dir = tmp_path / "run"

    log = execute_cadquery_file(code_path, output_dir)

    assert log.success is False
    assert log.status == "syntax_error"
    assert "SyntaxError" in (log.error or "")
    assert not (output_dir / "generated.step").exists()
    assert read_log(output_dir)["status"] == "syntax_error"


def test_execute_cadquery_file_fails_cleanly_when_result_is_missing(tmp_path):
    code_path = write_code(tmp_path, "x = 1\n")
    output_dir = tmp_path / "run"

    log = execute_cadquery_file(code_path, output_dir)

    assert log.success is False
    assert log.status == "missing_result"
    assert "`result`" in (log.error or "")
    assert read_log(output_dir)["status"] == "missing_result"


def test_execute_cadquery_file_times_out_and_still_writes_log(tmp_path):
    code_path = write_code(tmp_path, "while True:\n    pass\n")
    output_dir = tmp_path / "run"

    log = execute_cadquery_file(code_path, output_dir, timeout_seconds=0.2)

    assert log.success is False
    assert log.status == "timeout"
    assert "timed out" in (log.error or "")
    assert read_log(output_dir)["status"] == "timeout"


def test_execute_cadquery_cli_returns_nonzero_for_invalid_code_and_writes_log(tmp_path):
    code_path = write_code(tmp_path, "x = 1\n")
    output_dir = tmp_path / "run"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "legacy_part_bench.sandbox.execute_cadquery",
            "--code-file",
            str(code_path),
            "--output-dir",
            str(output_dir),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert read_log(output_dir)["status"] == "missing_result"

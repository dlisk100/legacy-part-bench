import json
import subprocess

from legacy_part_bench.sandbox.execute_cadquery import ExecutionLog
from legacy_part_bench.sandbox.sandbox_runner import (
    DockerSandboxConfig,
    build_sandbox_image,
    docker_run_command,
    run_in_docker_sandbox,
)


def test_docker_run_command_uses_no_network_limits_and_mounts(tmp_path):
    code_path = tmp_path / "answer.py"
    output_dir = tmp_path / "run"
    code_path.write_text("x = 1\n", encoding="utf-8")
    output_dir.mkdir()

    command = docker_run_command(
        code_path.resolve(),
        output_dir.resolve(),
        DockerSandboxConfig(image="lpb-test", timeout_seconds=12, memory="512m", cpus="0.5"),
    )

    assert command[:7] == ["docker", "run", "--rm", "--platform", "linux/amd64", "--network", "none"]
    assert "--cpus" in command
    assert "0.5" in command
    assert "--memory" in command
    assert "512m" in command
    assert f"type=bind,src={code_path.resolve()},dst=/work/input.py,readonly" in command
    assert f"type=bind,src={output_dir.resolve()},dst=/work/output" in command
    assert "lpb-test" in command


def test_build_sandbox_image_uses_buildx_when_platform_is_requested(monkeypatch, tmp_path):
    captured = {}

    def fake_run(command, text, capture_output, check):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("legacy_part_bench.sandbox.sandbox_runner.subprocess.run", fake_run)

    build_sandbox_image(
        image="lpb-test",
        dockerfile=tmp_path / "Dockerfile",
        context_dir=tmp_path,
        platform="linux/amd64",
    )

    assert captured["command"][:7] == [
        "docker",
        "buildx",
        "build",
        "--load",
        "--platform",
        "linux/amd64",
        "-t",
    ]


def test_docker_runner_writes_failure_log_when_docker_is_missing(tmp_path):
    code_path = tmp_path / "answer.py"
    output_dir = tmp_path / "run"
    code_path.write_text("x = 1\n", encoding="utf-8")

    log = run_in_docker_sandbox(
        code_path,
        output_dir,
        config=DockerSandboxConfig(docker_executable="definitely-not-docker"),
    )

    assert log.success is False
    assert log.status == "runtime_error"
    assert (output_dir / "execution_log.json").exists()


def test_docker_runner_uses_container_log_when_available(monkeypatch, tmp_path):
    code_path = tmp_path / "answer.py"
    output_dir = tmp_path / "run"
    code_path.write_text("x = 1\n", encoding="utf-8")

    def fake_which(executable):
        assert executable == "docker"
        return "/usr/bin/docker"

    def fake_run(command, text, capture_output, timeout, check):
        assert "--network" in command
        output_dir.mkdir(parents=True, exist_ok=True)
        log = ExecutionLog(
            success=False,
            status="missing_result",
            code_path="/work/input.py",
            output_dir="/work/output",
            error="Generated code did not assign `result`.",
        )
        (output_dir / "execution_log.json").write_text(
            json.dumps(log.to_dict()) + "\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 1, stdout="container stdout", stderr="")

    monkeypatch.setattr("legacy_part_bench.sandbox.sandbox_runner.shutil.which", fake_which)
    monkeypatch.setattr("legacy_part_bench.sandbox.sandbox_runner.subprocess.run", fake_run)

    log = run_in_docker_sandbox(code_path, output_dir)

    assert log.success is False
    assert log.status == "missing_result"
    assert "container stdout" in log.stdout

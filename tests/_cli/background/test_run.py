import signal
import subprocess
import time
from pathlib import Path

import boto3
import pytest
from inline_snapshot import snapshot
from typer.testing import CliRunner

from aws_annoying._cli.main import app
from tests._cli._helpers import normalize_console_output

runner = CliRunner()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("use_moto_server"),
]


def test_no_command() -> None:
    """Test that running without specifying a command to execute fails."""
    # Act
    result = runner.invoke(app, ["background", "run"])

    # Assert
    assert result.exit_code == 1
    assert normalize_console_output(result.stdout) == snapshot("🚨 No command specified to run in the background.")
    assert result.stderr == ""


def test_run_command(tmp_path: Path) -> None:
    """Test running a valid background command, verifying its execution and log outputs."""
    # Arrange
    ecs = boto3.client("ecs")
    family = "bg-task"
    for i in range(1, 4):
        ecs.register_task_definition(
            family=family,
            containerDefinitions=[
                {
                    "name": "container",
                    "image": f"image:{i}",
                    "cpu": 0,
                    "memory": 0,
                },
            ],
        )

    pid_file = tmp_path / "test.pid"
    log_file = tmp_path / "test.log"

    # Act
    result = runner.invoke(
        app,
        [
            "background",
            "run",
            "--pid-file",
            str(pid_file),
            "--log-file",
            str(log_file),
            "--",
            "ecs",
            "task-definition-lifecycle",
            "--family",
            family,
            "--keep-latest",
            "1",
        ],
    )

    # Assert
    assert result.exit_code == 0
    assert pid_file.exists()
    pid = int(pid_file.read_text().strip())
    assert pid > 0

    for _ in range(50):
        if log_file.exists() and "Deregistered" in log_file.read_text():
            break
        time.sleep(0.1)

    active = ecs.list_task_definitions(familyPrefix=family, status="ACTIVE")
    assert len(active["taskDefinitionArns"]) == 1
    assert active["taskDefinitionArns"][0].endswith(f"{family}:3")

    log_content = log_file.read_text()
    assert "Deregistered" in log_content

    assert normalize_console_output(
        result.stdout,
        replace={
            str(tmp_path): "<tmp_path>",
            str(pid): "<pid>",
        },
    ) == snapshot("""\
🔔 Starting background process: <PYTHON_EXECUTABLE> -m aws_annoying._cli.main ecs task-definition-lifecycle --family bg-task --keep-latest 1
🔔 Process started with PID <pid>. Outputs will be logged to <tmp_path>/test.log.
🔔 PID file written to <tmp_path>/test.pid.\
""")
    assert result.stderr == ""


def test_existing_pid_file_error(tmp_path: Path) -> None:
    """Test that running a command fails when a PID file already exists."""
    # Arrange
    pid_file = tmp_path / "test.pid"
    pid_file.write_text("12345")

    # Act
    result = runner.invoke(
        app,
        [
            "background",
            "run",
            "--pid-file",
            str(pid_file),
            "--",
            "ecs",
            "task-definition-lifecycle",
            "--family",
            "my-task",
        ],
    )

    # Assert
    assert result.exit_code == 1
    assert normalize_console_output(result.stdout, replace={str(tmp_path): "<tmp_path>"}) == snapshot(
        "🚨 PID file already exists: <tmp_path>/test.pid"
    )
    assert result.stderr == ""


def test_existing_pid_file_terminate(tmp_path: Path, dummy_process: subprocess.Popen[bytes]) -> None:
    """Test using `--terminate-running-process` to successfully kill the existing process and overwrite PID file."""
    # Arrange
    dummy_pid = dummy_process.pid

    pid_file = tmp_path / "test.pid"
    pid_file.write_text(str(dummy_pid))
    log_file = tmp_path / "test.log"

    # Act
    result = runner.invoke(
        app,
        [
            "background",
            "run",
            "--pid-file",
            str(pid_file),
            "--log-file",
            str(log_file),
            "--terminate-running-process",
            "--",
            "ecs",
            "task-definition-lifecycle",
            "--family",
            "my-task",
            "--keep-latest",
            "1",
        ],
    )

    # Assert
    assert result.exit_code == 0

    dummy_process.wait(timeout=2.0)
    assert dummy_process.returncode in (-signal.SIGTERM, signal.SIGTERM)

    new_pid = int(pid_file.read_text().strip())
    assert new_pid != dummy_pid
    assert new_pid > 0

    assert normalize_console_output(
        result.stdout,
        replace={
            str(tmp_path): "<tmp_path>",
            str(dummy_pid): "<dummy_pid>",
            str(new_pid): "<new_pid>",
        },
    ) == snapshot("""\
⚠️ Terminating running process with PID <dummy_pid>.
🔔 Removed the PID file <tmp_path>/test.pid.
🔔 Starting background process: <PYTHON_EXECUTABLE> -m aws_annoying._cli.main ecs task-definition-lifecycle --family my-task --keep-latest 1
🔔 Process started with PID <new_pid>. Outputs will be logged to <tmp_path>/test.log.
🔔 PID file written to <tmp_path>/test.pid.\
""")
    assert result.stderr == ""


def test_default_log_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that the default log file is created when no explicit log file path is provided."""
    # Arrange
    monkeypatch.chdir(tmp_path)
    pid_file = tmp_path / "test.pid"

    # Act
    result = runner.invoke(
        app,
        [
            "background",
            "run",
            "--pid-file",
            str(pid_file),
            "--",
            "ecs",
            "task-definition-lifecycle",
            "--family",
            "my-task",
            "--keep-latest",
            "1",
        ],
    )

    # Assert
    assert result.exit_code == 0
    pid = int(pid_file.read_text().strip())
    default_log = tmp_path / ".aws-annoying.log"

    for _ in range(50):
        if default_log.exists():
            break
        time.sleep(0.1)

    assert default_log.exists()

    assert normalize_console_output(
        result.stdout,
        replace={
            str(tmp_path): "<tmp_path>",
            str(pid): "<pid>",
        },
    ) == snapshot("""\
🔔 Starting background process: <PYTHON_EXECUTABLE> -m aws_annoying._cli.main ecs task-definition-lifecycle --family my-task --keep-latest 1
🔔 Process started with PID <pid>. Outputs will be logged to <tmp_path>/.aws-annoying.log.
🔔 PID file written to <tmp_path>/test.pid.\
""")
    assert result.stderr == ""


def test_default_pid_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that the default PID file is created when no explicit PID file path is provided."""
    # Arrange
    monkeypatch.chdir(tmp_path)
    log_file = tmp_path / "test.log"

    # Act
    result = runner.invoke(
        app,
        [
            "background",
            "run",
            "--log-file",
            str(log_file),
            "--",
            "ecs",
            "task-definition-lifecycle",
            "--family",
            "my-task",
            "--keep-latest",
            "1",
        ],
    )

    # Assert
    assert result.exit_code == 0
    default_pid_file = tmp_path / ".aws-annoying.pid"
    assert default_pid_file.exists()
    pid = int(default_pid_file.read_text().strip())
    assert pid > 0

    assert normalize_console_output(
        result.stdout,
        replace={
            str(tmp_path): "<tmp_path>",
            str(pid): "<pid>",
        },
    ) == snapshot("""\
🔔 Starting background process: <PYTHON_EXECUTABLE> -m aws_annoying._cli.main ecs task-definition-lifecycle --family my-task --keep-latest 1
🔔 Process started with PID <pid>. Outputs will be logged to <tmp_path>/test.log.
🔔 PID file written to <tmp_path>/.aws-annoying.pid.\
""")
    assert result.stderr == ""

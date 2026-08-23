from __future__ import annotations

import contextlib
import signal
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import boto3
import pytest
from typer.testing import CliRunner

from aws_annoying.cli.main import app
from tests.cli._helpers import normalize_console_output

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_snapshot.plugin import Snapshot

runner = CliRunner()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("use_moto_server"),
]


def test_no_command(snapshot: Snapshot) -> None:
    # Arrange & Act
    result = runner.invoke(app, ["background", "run"])

    # Assert
    assert result.exit_code == 1
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""


def test_dry_run(snapshot: Snapshot, tmp_path: Path) -> None:
    # Arrange
    pid_file = tmp_path / "test.pid"
    log_file = tmp_path / "test.log"

    # Act
    result = runner.invoke(
        app,
        [
            "--dry-run",
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
            "my-task",
        ],
    )

    # Assert
    assert result.exit_code == 0
    assert not pid_file.exists()
    snapshot.assert_match(
        normalize_console_output(result.stdout, replace={str(tmp_path): "<tmp_path>"}),
        "stdout.txt",
    )
    assert result.stderr == ""


def test_run_command(snapshot: Snapshot, tmp_path: Path) -> None:
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

    snapshot.assert_match(
        normalize_console_output(
            result.stdout,
            replace={
                str(tmp_path): "<tmp_path>",
                str(pid): "<pid>",
            },
        ),
        "stdout.txt",
    )
    assert result.stderr == ""


def test_existing_pid_file_error(snapshot: Snapshot, tmp_path: Path) -> None:
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
    snapshot.assert_match(
        normalize_console_output(result.stdout, replace={str(tmp_path): "<tmp_path>"}),
        "stdout.txt",
    )
    assert result.stderr == ""


def test_existing_pid_file_terminate(snapshot: Snapshot, tmp_path: Path) -> None:
    # Arrange
    dummy_proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    dummy_pid = dummy_proc.pid

    pid_file = tmp_path / "test.pid"
    pid_file.write_text(str(dummy_pid))
    log_file = tmp_path / "test.log"

    try:
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

        dummy_proc.wait(timeout=2.0)
        assert dummy_proc.returncode in (-signal.SIGTERM, signal.SIGTERM)

        new_pid = int(pid_file.read_text().strip())
        assert new_pid != dummy_pid
        assert new_pid > 0

        snapshot.assert_match(
            normalize_console_output(
                result.stdout,
                replace={
                    str(tmp_path): "<tmp_path>",
                    str(dummy_pid): "<dummy_pid>",
                    str(new_pid): "<new_pid>",
                },
            ),
            "stdout.txt",
        )
        assert result.stderr == ""
    finally:
        with contextlib.suppress(OSError):
            dummy_proc.kill()


def test_default_log_file(snapshot: Snapshot, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
    default_log = tmp_path / "background.log"

    for _ in range(50):
        if default_log.exists():
            break
        time.sleep(0.1)

    assert default_log.exists()

    snapshot.assert_match(
        normalize_console_output(
            result.stdout,
            replace={
                str(tmp_path): "<tmp_path>",
                str(pid): "<pid>",
            },
        ),
        "stdout.txt",
    )
    assert result.stderr == ""

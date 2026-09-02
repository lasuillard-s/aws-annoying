import signal
import subprocess
from pathlib import Path

import pytest
from inline_snapshot import snapshot
from typer.testing import CliRunner

from aws_annoying._cli.main import app
from tests._cli._helpers import normalize_console_output

runner = CliRunner()

pytestmark = [
    pytest.mark.unit,
]


def test_pid_file_not_found(tmp_path: Path) -> None:
    """Test that killing a process fails when the PID file does not exist."""
    # Arrange
    pid_file = tmp_path / "nonexistent.pid"

    # Act
    result = runner.invoke(app, ["background", "kill", "--pid-file", str(pid_file)])

    # Assert
    assert result.exit_code == 1
    assert normalize_console_output(result.stdout, replace={str(tmp_path): "<tmp_path>"}) == snapshot(
        "🚨 PID file not found: <tmp_path>/nonexistent.pid"
    )
    assert result.stderr == ""


def test_invalid_pid_content(tmp_path: Path) -> None:
    """Test that killing a process fails when the PID file contains invalid non-integer content."""
    # Arrange
    pid_file = tmp_path / "invalid.pid"
    pid_file.write_text("not-an-integer")

    # Act
    result = runner.invoke(app, ["background", "kill", "--pid-file", str(pid_file)])

    # Assert
    assert result.exit_code == 1
    assert normalize_console_output(result.stdout, replace={str(tmp_path): "<tmp_path>"}) == snapshot(
        "🚨 PID file content is invalid; expected integer, but got: 'not-an-integer'"
    )
    assert result.stderr == ""


def test_kill_process_success(tmp_path: Path, dummy_process: subprocess.Popen[bytes]) -> None:
    """Test that a running process is successfully killed and the PID file is removed."""
    # Arrange
    pid_file = tmp_path / "valid.pid"
    pid_file.write_text(str(dummy_process.pid))

    # Act
    result = runner.invoke(app, ["background", "kill", "--pid-file", str(pid_file)])

    # Assert
    assert result.exit_code == 0
    dummy_process.wait(timeout=2.0)
    # Return code is negative signal on POSIX, positive on Windows
    assert dummy_process.returncode in (-signal.SIGTERM, signal.SIGTERM)
    assert not pid_file.exists()
    assert normalize_console_output(
        result.stdout,
        replace={
            str(tmp_path): "<tmp_path>",
            str(dummy_process.pid): "<dummy_pid>",
        },
    ) == snapshot("""\
⚠️ Terminating running process with PID <dummy_pid>.
🔔 Removed the PID file <tmp_path>/valid.pid.
🔔 Terminated the background process successfully.\
""")
    assert result.stderr == ""


def test_kill_process_lookup_error(tmp_path: Path) -> None:
    """Test that killing a process handles non-existent PIDs gracefully and removes the PID file."""
    # Arrange
    pid_file = tmp_path / "valid.pid"
    pid_file.write_text("999999")

    # Act
    result = runner.invoke(app, ["background", "kill", "--pid-file", str(pid_file)])

    # Assert
    assert result.exit_code == 0
    assert not pid_file.exists()
    assert normalize_console_output(result.stdout, replace={str(tmp_path): "<tmp_path>"}) == snapshot("""\
⚠️ Terminating running process with PID 999999.
⚠️ Tried to terminate process with PID 999999 but does not exist.
🔔 Removed the PID file <tmp_path>/valid.pid.
🔔 Terminated the background process successfully.\
""")
    assert result.stderr == ""


def test_kill_no_remove(tmp_path: Path, dummy_process: subprocess.Popen[bytes]) -> None:
    """Test that killing a process succeeds but leaves the PID file intact when --no-remove is used."""
    # Arrange
    pid_file = tmp_path / "valid.pid"
    pid_file.write_text(str(dummy_process.pid))

    # Act
    result = runner.invoke(app, ["background", "kill", "--pid-file", str(pid_file), "--no-remove"])

    # Assert
    assert result.exit_code == 0
    dummy_process.wait(timeout=2.0)
    # Return code is negative signal on POSIX, positive on Windows
    assert dummy_process.returncode in (-signal.SIGTERM, signal.SIGTERM)
    assert pid_file.exists()
    assert normalize_console_output(
        result.stdout,
        replace={
            str(tmp_path): "<tmp_path>",
            str(dummy_process.pid): "<dummy_pid>",
        },
    ) == snapshot("""\
⚠️ Terminating running process with PID <dummy_pid>.
🔔 Terminated the background process successfully.\
""")
    assert pid_file.exists()
    assert result.stderr == ""


def test_kill_empty_pid_file(tmp_path: Path) -> None:
    """Test that killing a process handles empty PID files gracefully."""
    # Arrange
    pid_file = tmp_path / "empty.pid"
    pid_file.write_text("")

    # Act
    result = runner.invoke(app, ["background", "kill", "--pid-file", str(pid_file)])

    # Assert
    assert result.exit_code == 0
    assert not pid_file.exists()
    assert result.stderr == ""


def test_kill_empty_pid_file_no_remove(tmp_path: Path) -> None:
    """Test that killing a process handles empty PID files gracefully with --no-remove."""
    # Arrange
    pid_file = tmp_path / "empty.pid"
    pid_file.write_text("")

    # Act
    result = runner.invoke(app, ["background", "kill", "--pid-file", str(pid_file), "--no-remove"])

    # Assert
    assert result.exit_code == 0
    assert pid_file.exists()
    assert result.stderr == ""


def test_kill_default_pid_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    dummy_process: subprocess.Popen[bytes],
) -> None:
    """Test that killing a process uses the default PID file when no explicit path is provided."""
    # Arrange
    monkeypatch.chdir(tmp_path)
    pid_file = tmp_path / ".aws-annoying.pid"
    pid_file.write_text(str(dummy_process.pid))

    # Act
    result = runner.invoke(app, ["background", "kill"])

    # Assert
    assert result.exit_code == 0
    dummy_process.wait(timeout=2.0)
    # Return code is negative signal on POSIX, positive on Windows
    assert dummy_process.returncode in (-signal.SIGTERM, signal.SIGTERM)
    assert not pid_file.exists()
    assert normalize_console_output(
        result.stdout,
        replace={
            str(tmp_path): "<tmp_path>",
            str(dummy_process.pid): "<dummy_pid>",
        },
    ) == snapshot("""\
⚠️ Terminating running process with PID <dummy_pid>.
🔔 Removed the PID file .aws-annoying.pid.
🔔 Terminated the background process successfully.\
""")
    assert result.stderr == ""

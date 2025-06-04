from __future__ import annotations

import pytest
from typer.testing import CliRunner

from aws_annoying.cli.main import app
from aws_annoying.session_manager import SessionManager
from tests._helpers import ci_only, run_if_macos, run_if_windows, skip_if_macos, skip_if_windows

runner = CliRunner()

pytestmark = [
    pytest.mark.integration,
    ci_only,
]


@skip_if_macos
@skip_if_windows
def test_install_linux() -> None:
    # Arrange
    session_manager = SessionManager()
    assert session_manager.verify_installation() == (False, None, None)

    # Act
    result = runner.invoke(app, ["session-manager", "install", "--yes"])

    # Assert
    assert result.exit_code == 0, result.stdout
    is_installed, binary_path, version = session_manager.verify_installation()
    assert is_installed is True
    assert binary_path
    assert binary_path.is_file()
    assert version is not None


@run_if_macos
def test_install_macos() -> None:
    # Arrange
    session_manager = SessionManager()
    assert session_manager.verify_installation() == (False, None, None)

    # Act
    result = runner.invoke(app, ["session-manager", "install", "--yes"])

    # Assert
    assert result.exit_code == 0, result.stdout
    is_installed, binary_path, version = session_manager.verify_installation()
    assert is_installed is True
    assert binary_path
    assert binary_path.is_file()
    assert version is not None


@run_if_windows
def test_install_windows() -> None:
    # Arrange
    session_manager = SessionManager()
    assert session_manager.verify_installation() == (False, None, None)

    # Act
    result = runner.invoke(app, ["session-manager", "install", "--yes"])

    # Assert
    assert result.exit_code == 0, result.stdout
    is_installed, binary_path, version = session_manager.verify_installation()
    assert is_installed is True
    assert binary_path
    assert binary_path.is_file()
    assert version is not None

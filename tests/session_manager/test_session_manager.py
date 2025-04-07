from __future__ import annotations

import pytest
from typer.testing import CliRunner

from aws_annoying.main import app
from aws_annoying.session_manager.session_manager import SessionManager
from aws_annoying.utils.downloader import DummyDownloader

runner = CliRunner()


@pytest.mark.macos
def test_macos_session_manager_install() -> None:
    # Arrange
    # ...

    # Act
    runner.invoke(app, ["session-manager", "install"])

    # Assert
    session_manager = SessionManager(downloader=DummyDownloader())
    is_installed, binary_path, version = session_manager.verify_installation()
    assert is_installed is True
    assert binary_path is not None
    assert version is not None


@pytest.mark.windows
def test_windows_session_manager_install() -> None:
    # Arrange
    # ...

    # Act
    runner.invoke(app, ["session-manager", "install"])

    # Assert
    session_manager = SessionManager(downloader=DummyDownloader())
    is_installed, binary_path, version = session_manager.verify_installation()
    assert is_installed is True
    assert binary_path is not None
    assert version is not None

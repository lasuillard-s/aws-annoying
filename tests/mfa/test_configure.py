from __future__ import annotations

from configparser import ConfigParser
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from typer.testing import CliRunner

from aws_annoying.main import app
from tests._helpers import normalize_console_output

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_snapshot.plugin import Snapshot

runner = CliRunner()

pytestmark = [
    pytest.mark.unit,
    pytest.mark.usefixtures("use_moto"),
]


def test_basic(snapshot: Snapshot, tmp_path: Path) -> None:
    """The command should deregister the oldest task definitions."""
    # Arrange

    # Act
    mfa_profile = "mfa"
    aws_credentials = tmp_path / "credentials"
    aws_config = tmp_path / "config"
    result = runner.invoke(
        app,
        [
            "mfa",
            "configure",
            "--mfa-profile",
            mfa_profile,
            "--mfa-source-profile",
            "default",
            "--mfa-serial-number",
            "1234567890",
            "--mfa-token-code",
            "123456",
            "--aws-credentials",
            str(aws_credentials),
            "--aws-config",
            str(aws_config),
        ],
    )

    # Assert
    assert result.exit_code == 0
    stdout = result.stdout.replace(str(tmp_path), "<tmp_path>")
    snapshot.assert_match(normalize_console_output(stdout), "stdout.txt")

    ini = ConfigParser()
    ini.read(aws_credentials)
    assert ini[mfa_profile] == {
        "aws_access_key_id": mock.ANY,
        "aws_secret_access_key": mock.ANY,
        "aws_session_token": mock.ANY,
    }

    snapshot.assert_match(aws_config.read_text(), "aws_config.txt")

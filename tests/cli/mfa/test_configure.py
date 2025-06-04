from __future__ import annotations

from configparser import ConfigParser
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from typer.testing import CliRunner

from aws_annoying.cli.main import app
from aws_annoying.mfa_config import MfaConfig
from tests.cli._helpers import normalize_console_output

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_snapshot.plugin import Snapshot

runner = CliRunner()

pytestmark = [
    pytest.mark.unit,
    pytest.mark.usefixtures("use_moto"),
]


@pytest.mark.parametrize("skip_persist", [True, False], ids=["skip_persist", "persist"])
def test_basic(snapshot: Snapshot, tmp_path: Path, skip_persist: bool) -> None:  # noqa: FBT001
    """The command should configure MFA settings."""
    # Arrange
    mfa_profile = "mfa"
    aws_credentials = tmp_path / "credentials"
    aws_config = tmp_path / "config"

    # Act
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
            *(["--no-persist"] if skip_persist else []),
        ],
    )

    # Assert
    assert result.exit_code == 0
    snapshot.assert_match(
        normalize_console_output(result.stdout, replace={str(tmp_path): "<tmp_path>"}),
        "stdout.txt",
    )

    ini = ConfigParser()
    ini.read(aws_credentials)
    assert ini[mfa_profile] == {
        "aws_access_key_id": mock.ANY,
        "aws_secret_access_key": mock.ANY,
        "aws_session_token": mock.ANY,
    }

    if skip_persist:
        assert not aws_config.exists()
    else:
        snapshot.assert_match(aws_config.read_text(), "aws_config.ini")


def test_load_existing_config(snapshot: Snapshot, tmp_path: Path) -> None:
    """The command should load existing config if arguments not given."""
    # Arrange
    mfa_profile = "mfa"
    aws_credentials = tmp_path / "credentials"
    aws_config = tmp_path / "config"
    MfaConfig(
        mfa_profile=mfa_profile,
        mfa_source_profile="default",
        mfa_serial_number="1234567890",
    ).save_ini_file(aws_config, "aws-annoying:mfa")

    # Act
    result = runner.invoke(
        app,
        [
            "mfa",
            "configure",
            "--aws-credentials",
            str(aws_credentials),
            "--aws-config",
            str(aws_config),
            "--mfa-token-code",
            "123456",
        ],
    )

    # Assert
    assert result.exit_code == 0
    snapshot.assert_match(
        normalize_console_output(result.stdout, replace={str(tmp_path): "<tmp_path>"}),
        "stdout.txt",
    )

    ini = ConfigParser()
    ini.read(aws_credentials)
    assert ini[mfa_profile] == {
        "aws_access_key_id": mock.ANY,
        "aws_secret_access_key": mock.ANY,
        "aws_session_token": mock.ANY,
    }

    snapshot.assert_match(aws_config.read_text(), "aws_config.ini")


def test_dry_run(snapshot: Snapshot, tmp_path: Path) -> None:
    """If dry-run mode enabled, configuration shouldn't updated."""
    # Arrange
    mfa_profile = "mfa"
    aws_credentials = tmp_path / "credentials"
    aws_config = tmp_path / "config"

    # Act
    result = runner.invoke(
        app,
        [
            "--dry-run",
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
    snapshot.assert_match(
        normalize_console_output(result.stdout, replace={str(tmp_path): "<tmp_path>"}),
        "stdout.txt",
    )

    ini = ConfigParser()
    ini.read(aws_credentials)
    assert mfa_profile not in ini
    assert not aws_config.exists()

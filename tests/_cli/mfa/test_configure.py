from __future__ import annotations

from configparser import ConfigParser
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from typer.testing import CliRunner

from aws_annoying._cli.main import app
from aws_annoying._cli.mfa.configure import _MfaConfig, _update_config, _update_credentials
from tests._cli._helpers import normalize_console_output

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_snapshot.plugin import Snapshot

runner = CliRunner()

pytestmark = [
    pytest.mark.unit,
    pytest.mark.cli,
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
            "--mfa-region",
            "us-west-2",
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
        config_ini = ConfigParser()
        config_ini.read(aws_config)
        assert config_ini["profile mfa"]["region"] == "us-west-2"
        assert not config_ini.has_section("aws-annoying:mfa")
    else:
        snapshot.assert_match(aws_config.read_text(), "aws_config.ini")


def test_load_existing_config(snapshot: Snapshot, tmp_path: Path) -> None:
    """The command should load existing config if arguments not given."""
    # Arrange
    mfa_profile = "mfa"
    aws_credentials = tmp_path / "credentials"
    aws_config = tmp_path / "config"
    _MfaConfig(
        mfa_profile=mfa_profile,
        mfa_source_profile="default",
        mfa_serial_number="1234567890",
        mfa_region="us-west-2",
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


def test_mfa_config_region_persistence(tmp_path: Path) -> None:
    """`_MfaConfig` should save and load mfa_region to/from ini file."""
    config_file = tmp_path / "config"
    cfg = _MfaConfig(
        mfa_profile="default",
        mfa_source_profile="mfa",
        mfa_serial_number="123456",
        mfa_region="us-west-2",
    )
    cfg.save_ini_file(config_file, "aws-annoying:mfa")

    loaded, exists = _MfaConfig.from_ini_file(config_file, "aws-annoying:mfa")
    assert exists
    assert loaded.mfa_region == "us-west-2"
    assert loaded.mfa_profile == "default"
    assert loaded.mfa_source_profile == "mfa"


def test_update_config_default_profile(tmp_path: Path) -> None:
    """`_update_config` should set region under `[default]` for default profile."""
    config_file = tmp_path / "config"
    _update_config(config_file, "default", region="us-east-1")

    ini = ConfigParser()
    ini.read(config_file)
    assert ini["default"]["region"] == "us-east-1"


def test_update_config_custom_profile(tmp_path: Path) -> None:
    """`_update_config` should set region under `[profile <name>]` for custom profile."""
    config_file = tmp_path / "config"
    _update_config(config_file, "custom", region="eu-west-1")

    ini = ConfigParser()
    ini.read(config_file)
    assert ini["profile custom"]["region"] == "eu-west-1"


def test_update_config_none_region(tmp_path: Path) -> None:
    """`_update_config` should do nothing if region is None."""
    config_file = tmp_path / "config"
    _update_config(config_file, "default", region=None)
    assert not config_file.exists()


def test_mfa_config_nonexistent_section(tmp_path: Path) -> None:
    """`_MfaConfig.from_ini_file` should return empty config if section does not exist."""
    config_file = tmp_path / "config"
    loaded, exists = _MfaConfig.from_ini_file(config_file, "nonexistent")
    assert not exists
    assert loaded == _MfaConfig()


def test_mfa_config_extra_fields(tmp_path: Path) -> None:
    """`_MfaConfig.from_ini_file` should ignore unexpected fields in ini file."""
    config_file = tmp_path / "config"
    ini = ConfigParser()
    ini["aws-annoying:mfa"] = {
        "mfa_profile": "custom",
        "unknown_key": "some_value",
    }
    with config_file.open("w") as f:
        ini.write(f)

    loaded, exists = _MfaConfig.from_ini_file(config_file, "aws-annoying:mfa")
    assert exists
    assert loaded.mfa_profile == "custom"
    assert not hasattr(loaded, "unknown_key")


def test_update_credentials(tmp_path: Path) -> None:
    """`_update_credentials` should write credentials to specified profile."""
    creds_file = tmp_path / "credentials"
    _update_credentials(
        creds_file,
        "default",
        access_key="AKIAEXAMPLE",
        secret_key="SECRETEXAMPLE",  # noqa: S106
        session_token="TOKENEXAMPLE",  # noqa: S106
    )

    ini = ConfigParser()
    ini.read(creds_file)
    assert ini["default"]["aws_access_key_id"] == "AKIAEXAMPLE"
    assert ini["default"]["aws_secret_access_key"] == "SECRETEXAMPLE"  # noqa: S105
    assert ini["default"]["aws_session_token"] == "TOKENEXAMPLE"  # noqa: S105

from __future__ import annotations

from configparser import ConfigParser
from typing import TYPE_CHECKING

from aws_annoying.mfa_config import MfaConfig, update_config, update_credentials

if TYPE_CHECKING:
    from pathlib import Path


def test_mfa_config_region_persistence(tmp_path: Path) -> None:
    """`MfaConfig` should save and load mfa_region to/from ini file."""
    config_file = tmp_path / "config"
    cfg = MfaConfig(
        mfa_profile="default",
        mfa_source_profile="mfa",
        mfa_serial_number="123456",
        mfa_region="us-west-2",
    )
    cfg.save_ini_file(config_file, "aws-annoying:mfa")

    loaded, exists = MfaConfig.from_ini_file(config_file, "aws-annoying:mfa")
    assert exists
    assert loaded.mfa_region == "us-west-2"
    assert loaded.mfa_profile == "default"
    assert loaded.mfa_source_profile == "mfa"


def test_update_config_default_profile(tmp_path: Path) -> None:
    """`update_config` should set region under `[default]` for default profile."""
    config_file = tmp_path / "config"
    update_config(config_file, "default", region="us-east-1")

    ini = ConfigParser()
    ini.read(config_file)
    assert ini["default"]["region"] == "us-east-1"


def test_update_config_custom_profile(tmp_path: Path) -> None:
    """`update_config` should set region under `[profile <name>]` for custom profile."""
    config_file = tmp_path / "config"
    update_config(config_file, "custom", region="eu-west-1")

    ini = ConfigParser()
    ini.read(config_file)
    assert ini["profile custom"]["region"] == "eu-west-1"


def test_update_config_none_region(tmp_path: Path) -> None:
    """`update_config` should do nothing if region is None."""
    config_file = tmp_path / "config"
    update_config(config_file, "default", region=None)
    assert not config_file.exists()


def test_mfa_config_nonexistent_section(tmp_path: Path) -> None:
    """`MfaConfig.from_ini_file` should return empty config if section does not exist."""
    config_file = tmp_path / "config"
    loaded, exists = MfaConfig.from_ini_file(config_file, "nonexistent")
    assert not exists
    assert loaded == MfaConfig()


def test_mfa_config_extra_fields(tmp_path: Path) -> None:
    """`MfaConfig.from_ini_file` should ignore unexpected fields in ini file."""
    config_file = tmp_path / "config"
    ini = ConfigParser()
    ini["aws-annoying:mfa"] = {
        "mfa_profile": "custom",
        "unknown_key": "some_value",
    }
    with config_file.open("w") as f:
        ini.write(f)

    loaded, exists = MfaConfig.from_ini_file(config_file, "aws-annoying:mfa")
    assert exists
    assert loaded.mfa_profile == "custom"
    assert not hasattr(loaded, "unknown_key")


def test_update_credentials(tmp_path: Path) -> None:
    """`update_credentials` should write credentials to specified profile."""
    creds_file = tmp_path / "credentials"
    update_credentials(
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

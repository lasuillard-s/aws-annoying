from __future__ import annotations

from configparser import ConfigParser
from typing import TYPE_CHECKING

from aws_annoying.mfa_config import MfaConfig, update_config

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

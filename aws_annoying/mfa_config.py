from __future__ import annotations

import configparser
import logging
from pathlib import Path  # noqa: TC003
from typing import Optional

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class MfaConfig(BaseModel):
    """MFA configuration for AWS profiles."""

    model_config = ConfigDict(extra="ignore")

    mfa_profile: Optional[str] = None
    mfa_source_profile: Optional[str] = None
    mfa_serial_number: Optional[str] = None

    def save_ini_file(self, path: Path, section_key: str) -> None:
        """Save configuration to an AWS config file."""
        config_ini = configparser.ConfigParser()
        config_ini.read(path)
        config_ini.setdefault(section_key, {})
        for k, v in self.model_dump(exclude_none=True).items():
            config_ini[section_key][k] = v

        with path.open("w") as f:
            config_ini.write(f)

        logger.debug("Saved config to %s with section %s", path, section_key)

    @classmethod
    def from_ini_file(cls, path: Path, section_key: str) -> tuple[MfaConfig, bool]:
        """Load configuration from an AWS config file, with boolean indicating if the config already exists."""
        logger.debug("Loading config from %s with section %s", path, section_key)
        config_ini = configparser.ConfigParser()
        config_ini.read(path)
        if config_ini.has_section(section_key):
            section = dict(config_ini.items(section_key))
            return cls.model_validate(section), True

        return cls(), False


def update_credentials(path: Path, profile: str, *, access_key: str, secret_key: str, session_token: str) -> None:
    """Update AWS credentials file with the provided profile and credentials."""
    credentials_ini = configparser.ConfigParser()
    credentials_ini.read(path)
    credentials_ini.setdefault(profile, {})
    credentials_ini[profile]["aws_access_key_id"] = access_key
    credentials_ini[profile]["aws_secret_access_key"] = secret_key
    credentials_ini[profile]["aws_session_token"] = session_token
    with path.open("w") as f:
        credentials_ini.write(f)

    logger.debug("Updated credentials file %s with profile %s", path, profile)

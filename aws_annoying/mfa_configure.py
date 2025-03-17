from __future__ import annotations

import configparser
from pathlib import Path  # noqa: TC003
from typing import Optional

import boto3
import typer
from pydantic import BaseModel, ConfigDict
from rich import print  # noqa: A004
from rich.prompt import Prompt

from .app import app

_CONFIG_INI_SECTION = "aws-annoying:mfa"

mfa_app = typer.Typer(no_args_is_help=True)
app.add_typer(mfa_app, name="mfa")


@mfa_app.command()
def configure(  # noqa: PLR0913
    *,
    mfa_profile: str = typer.Option(
        "mfa",
        help="The MFA profile to configure.",
    ),
    mfa_serial_number: Optional[str] = typer.Option(
        None,
        help="The MFA device serial number. It is required if not persisted in configuration.",
        show_default=False,
    ),
    mfa_token_code: Optional[str] = typer.Option(
        None,
        help="The MFA token code.",
        show_default=False,
    ),
    aws_credentials: Path = typer.Option(  # noqa: B008
        "~/.aws/credentials",
        help="The path to the AWS credentials file.",
    ),
    aws_config: Path = typer.Option(  # noqa: B008
        "~/.aws/config",
        help="The path to the AWS config file. Used to persist the MFA configuration.",
    ),
    persist: bool = typer.Option(
        True,  # noqa: FBT003
        help="Persist the MFA configuration.",
    ),
) -> None:
    """Configure AWS profile for MFA."""
    # Expand user home directory
    aws_credentials = aws_credentials.expanduser()
    aws_config = aws_config.expanduser()

    # Load configuration
    mfa_config, exists = _MfaConfig.from_ini_file(aws_config, _CONFIG_INI_SECTION)
    if exists:
        print(f"⚙️ Loaded MFA configuration from AWS config ({aws_config}).")

    mfa_config.mfa_serial_number = (
        mfa_serial_number or mfa_config.mfa_serial_number or Prompt.ask("🔒 Enter MFA serial number")
    )
    mfa_token_code = mfa_token_code or Prompt.ask("🔑 Enter MFA token code")

    # Get credentials
    print("💬 Retrieving MFA credentials")
    sts = boto3.client("sts")
    response = sts.get_session_token(
        SerialNumber=mfa_config.mfa_serial_number,
        TokenCode=mfa_token_code,
    )
    credentials = response["Credentials"]

    # Update MFA profile in AWS credentials
    print(f"✅ Updating MFA profile ({mfa_profile}) to AWS credentials ({aws_credentials})")
    credentials_ini = configparser.ConfigParser()
    credentials_ini.read(aws_credentials)
    section = mfa_profile

    credentials_ini.setdefault(section, {})
    credentials_ini[section]["aws_access_key_id"] = credentials["AccessKeyId"]
    credentials_ini[section]["aws_secret_access_key"] = credentials["SecretAccessKey"]
    credentials_ini[section]["aws_session_token"] = credentials["SessionToken"]
    with aws_credentials.open("w") as f:
        credentials_ini.write(f)

    # Persist MFA configuration
    if persist:
        print(
            f"✅ Persisting MFA configuration in AWS config ({aws_config}),"
            f" in [bold]{_CONFIG_INI_SECTION}[/bold] section.",
        )
        mfa_config.save_ini_file(aws_config, _CONFIG_INI_SECTION)
    else:
        print("⚠️ MFA configuration not persisted.")


class _MfaConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mfa_serial_number: Optional[str] = None

    def save_ini_file(self, path: Path, section_key: str) -> None:
        """Save configuration to an AWS config file."""
        config_ini = configparser.ConfigParser()
        config_ini.read(path)
        config_ini.setdefault(section_key, {})
        for k, v in self.model_dump().items():
            config_ini[section_key][k] = v

        with path.open("w") as f:
            config_ini.write(f)

    @classmethod
    def from_ini_file(cls, path: Path, section_key: str) -> tuple[_MfaConfig, bool]:
        """Load configuration from an AWS config file, with boolean indicating if the config already exists."""
        config_ini = configparser.ConfigParser()
        config_ini.read(path)
        if config_ini.has_section(section_key):
            section = dict(config_ini.items(section_key))
            return cls.model_validate(section), True

        return cls(), False

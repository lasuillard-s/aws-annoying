from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import Optional

import boto3
import typer
from rich import print  # noqa: A004
from rich.prompt import Prompt

from aws_annoying.mfa import MfaConfig, update_credentials

from ._app import mfa_app

_CONFIG_INI_SECTION = "aws-annoying:mfa"


@mfa_app.command()
def configure(  # noqa: PLR0913
    *,
    mfa_profile: Optional[str] = typer.Option(
        None,
        help="The MFA profile to configure.",
    ),
    mfa_source_profile: Optional[str] = typer.Option(
        None,
        help="The AWS profile to use to retrieve MFA credentials.",
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
    mfa_config, exists = MfaConfig.from_ini_file(aws_config, _CONFIG_INI_SECTION)
    if exists:
        print(f"⚙️ Loaded MFA configuration from AWS config ({aws_config}).")

    mfa_profile = (
        mfa_profile
        or mfa_config.mfa_profile
        # _
        or Prompt.ask("👤 Enter name of MFA profile to configure", default="mfa")
    )
    mfa_source_profile = (
        mfa_source_profile
        or mfa_config.mfa_source_profile
        or Prompt.ask("👤 Enter AWS profile to use to retrieve MFA credentials", default="default")
    )
    mfa_serial_number = (
        mfa_serial_number
        or mfa_config.mfa_serial_number
        # _
        or Prompt.ask("🔒 Enter MFA serial number")
    )
    mfa_token_code = (
        mfa_token_code
        # _
        or Prompt.ask("🔑 Enter MFA token code")
    )

    # Get credentials
    print(f"💬 Retrieving MFA credentials using profile [bold]{mfa_source_profile}[/bold]")
    session = boto3.session.Session(profile_name=mfa_source_profile)
    sts = session.client("sts")
    response = sts.get_session_token(
        SerialNumber=mfa_serial_number,
        TokenCode=mfa_token_code,
    )
    credentials = response["Credentials"]

    # Update MFA profile in AWS credentials
    print(f"✅ Updating MFA profile ([bold]{mfa_profile}[/bold]) to AWS credentials ({aws_credentials})")
    update_credentials(
        aws_credentials,
        mfa_profile,  # type: ignore[arg-type]
        access_key=credentials["AccessKeyId"],
        secret_key=credentials["SecretAccessKey"],
        session_token=credentials["SessionToken"],
    )

    # Persist MFA configuration
    if persist:
        print(
            f"✅ Persisting MFA configuration in AWS config ({aws_config}),"
            f" in [bold]{_CONFIG_INI_SECTION}[/bold] section.",
        )
        mfa_config.mfa_profile = mfa_profile
        mfa_config.mfa_source_profile = mfa_source_profile
        mfa_config.mfa_serial_number = mfa_serial_number
        mfa_config.save_ini_file(aws_config, _CONFIG_INI_SECTION)
    else:
        print("⚠️ MFA configuration not persisted.")

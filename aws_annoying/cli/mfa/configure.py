from __future__ import annotations

import logging
from pathlib import Path  # noqa: TC003
from typing import Optional

import boto3
import typer
from rich.prompt import Prompt

from aws_annoying.mfa_config import MfaConfig, update_config, update_credentials

from ._app import mfa_app

logger = logging.getLogger(__name__)


@mfa_app.command()
def configure(  # noqa: PLR0913
    ctx: typer.Context,
    *,
    mfa_profile: Optional[str] = typer.Option(
        None,
        help="The MFA profile to configure.",
    ),
    mfa_source_profile: Optional[str] = typer.Option(
        None,
        help="The AWS profile to use to retrieve MFA credentials.",
    ),
    mfa_region: Optional[str] = typer.Option(
        None,
        help="The AWS region for the MFA profile.",
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
    aws_config_section: str = typer.Option(
        "aws-annoying:mfa",
        help="The section in the AWS config file to persist the MFA configuration.",
    ),
    persist: bool = typer.Option(
        True,  # noqa: FBT003
        help="Persist the MFA configuration.",
    ),
) -> None:
    r"""Configure AWS profile for MFA.

    This command retrieves temporary MFA credentials using the provided source profile (`--mfa-source-profile`)
    and MFA token code then updates the specified AWS profile with these credentials.

    Before running this command, ensure that your source profile (default: `mfa`) is configured in AWS CLI
    (e.g., using `aws configure --profile mfa`).

    You can configure it interactively, by omitting the options, or provide them directly via command-line options.

    ```shell
    aws configure --profile mfa
    aws-annoying mfa configure
    ```

    If you want to specify a custom profile or source profile, you can pass them as options:

    ```shell
    aws configure --profile my-mfa-source
    aws-annoying mfa configure \
        --mfa-profile default \
        --mfa-source-profile my-mfa-source
    ```

    Required IAM Permissions:

    - `sts:GetSessionToken`
    """
    dry_run = ctx.meta["dry_run"]

    # Expand user home directory
    aws_credentials = aws_credentials.expanduser()
    aws_config = aws_config.expanduser()

    # Load configuration
    mfa_config, exists = MfaConfig.from_ini_file(aws_config, aws_config_section)
    if exists:
        logger.info("Loaded MFA configuration from AWS config (%s).", aws_config)

    mfa_profile = (
        mfa_profile
        or mfa_config.mfa_profile
        # _
        or Prompt.ask("👤 Enter name of MFA profile to configure", default="default")
    )
    mfa_source_profile = (
        mfa_source_profile
        or mfa_config.mfa_source_profile
        or Prompt.ask("👤 Enter AWS profile to use to retrieve MFA credentials", default="mfa")
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
    logger.info("Retrieving MFA credentials using profile [bold]%s[/bold]", mfa_source_profile)
    session = boto3.session.Session(profile_name=mfa_source_profile)

    # Prompt user to enter AWS region for the MFA profile. Defaults to the region
    # from the source profile.
    mfa_region = (
        mfa_region
        or mfa_config.mfa_region
        or (
            Prompt.ask("🌐 Enter AWS region", default=session.region_name)
            if session.region_name
            else Prompt.ask("🌐 Enter AWS region")
        )
        or None
    )

    sts = session.client("sts", region_name=mfa_region)
    response = sts.get_session_token(
        SerialNumber=mfa_serial_number,
        TokenCode=mfa_token_code,
    )
    credentials = response["Credentials"]

    # Update MFA profile in AWS credentials
    logger.warning(
        "Updating MFA profile ([bold]%s[/bold]) to AWS credentials ([bold]%s[/bold])",
        mfa_profile,
        aws_credentials,
    )
    if not dry_run:
        update_credentials(
            aws_credentials,
            mfa_profile,  # type: ignore[arg-type]
            access_key=credentials["AccessKeyId"],
            secret_key=credentials["SecretAccessKey"],
            session_token=credentials["SessionToken"],
        )
        if mfa_region:
            update_config(
                aws_config,
                mfa_profile,  # type: ignore[arg-type]
                region=mfa_region,
            )

    # Persist MFA configuration
    if persist:
        logger.info(
            "Persisting MFA configuration in AWS config (%s), in [bold]%s[/bold] section.",
            aws_config,
            aws_config_section,
        )
        mfa_config.mfa_profile = mfa_profile
        mfa_config.mfa_source_profile = mfa_source_profile
        mfa_config.mfa_serial_number = mfa_serial_number
        mfa_config.mfa_region = mfa_region
        if not dry_run:
            mfa_config.save_ini_file(aws_config, aws_config_section)
    else:
        logger.warning("MFA configuration not persisted.")

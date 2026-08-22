from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any, Optional

import typer

from aws_annoying.ec2 import (
    InstanceChecker,
    InstanceNotFoundError,
    InstanceNotReadyError,
    InvalidInstanceIdError,
    detect_instance_platform,
    is_valid_instance_id,
    make_ssm_checker,
    wait_for_instance_ready,
)

from ._app import ec2_app

logger = logging.getLogger(__name__)


class PlatformChoice(str, Enum):
    """Platform choice for EC2 instance OS."""

    AUTO = "auto"
    LINUX = "linux"
    WINDOWS = "windows"


def _validate_json_str(ctx: typer.Context, param: typer.CallbackParam, value: Optional[str]) -> Any:
    """Validate if the provided string is a valid JSON string."""
    if value is None:
        return value

    try:
        json.loads(value)
    except json.JSONDecodeError as err:
        msg = "Failed to parse JSON argument"
        raise typer.BadParameter(msg, ctx, param) from err

    return value


@ec2_app.command()
def wait_for_ready(  # noqa: PLR0913
    ctx: typer.Context,
    *,
    instance_id: str = typer.Option(
        ...,
        "--instance-id",
        "-i",
        show_default=False,
        help="The ID of the EC2 instance to wait for (e.g. i-0123456789abcdef0).",
    ),
    platform: PlatformChoice = typer.Option(  # noqa: B008
        PlatformChoice.AUTO,
        "--platform",
        "-p",
        help="Target OS platform (auto, linux, windows). Custom SSM document takes precedence over this option.",
    ),
    max_attempts: int = typer.Option(
        10,
        "--max-attempts",
        help="Maximum number of attempts to check instance status.",
    ),
    delay: float = typer.Option(
        30.0,
        "--delay",
        help="Delay in seconds between attempts.",
    ),
    document_name: Optional[str] = typer.Option(
        None,
        "--document-name",
        help="Custom SSM document name override.",
    ),
    document_parameters: Optional[str] = typer.Option(
        None,
        "--document-parameters",
        help="JSON string of parameters to pass to the SSM document.",
        callback=_validate_json_str,
    ),
) -> None:
    """Wait for an EC2 instance to be ready to execute SSM commands.

    Required IAM Permissions:

    - `ec2:DescribeInstances` (when platform is 'auto' and no custom document is specified)
    - `ssm:SendCommand`
    - `ssm:GetCommandInvocation`
    """
    dry_run = ctx.meta.get("dry_run", False)

    # Check if the provided instance ID is valid
    if not is_valid_instance_id(instance_id):
        logger.error("Invalid EC2 instance ID '%s'", instance_id)
        raise typer.Exit(1)

    # Both document_name and document_parameters must be provided together
    if (document_name is None and document_parameters is not None) or (
        document_name is not None and document_parameters is None
    ):
        msg = "Both --document-name and --document-parameters must be provided together."
        raise typer.BadParameter(msg, ctx, param=None)

    # Determine the appropriate checker function based on platform choice or custom SSM document
    checker: InstanceChecker
    if document_name is not None and document_parameters is not None:
        parsed_parameters: dict[str, Any] = json.loads(document_parameters)
        checker = make_ssm_checker(document_name, parsed_parameters)
    else:
        if platform == PlatformChoice.AUTO:
            detected = detect_instance_platform(instance_id)
            platform = PlatformChoice.WINDOWS if detected == "windows" else PlatformChoice.LINUX

        match platform:
            case PlatformChoice.LINUX:
                checker = make_ssm_checker("AWS-RunShellScript", {"commands": ["echo 'ready'"]})
            case PlatformChoice.WINDOWS:
                checker = make_ssm_checker("AWS-RunPowerShellScript", {"commands": ["Write-Output 'ready'"]})
            case _:
                msg = f"Unsupported platform choice: {platform}"
                raise typer.BadParameter(msg, ctx, param=None)

    # Start waiting for the instance to be ready using the selected checker
    logger.info("Waiting for instance %s to be ready...", instance_id)
    if dry_run:
        logger.info("Dry-run mode is enabled and skipping actual wait for instance readiness.")
        return

    try:
        wait_for_instance_ready(
            instance_id=instance_id,
            checker=checker,
            max_attempts=max_attempts,
            delay=delay,
        )
    except (InvalidInstanceIdError, InstanceNotFoundError, InstanceNotReadyError) as err:
        logger.exception("Failed waiting for instance to be ready.")
        raise typer.Exit(1) from err
    else:
        logger.info("Instance %s is ready.", instance_id)

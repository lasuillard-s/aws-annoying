from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any, Optional

import boto3
import botocore.exceptions
import typer

from aws_annoying._cli.ec2._app import ec2_app
from aws_annoying.ec2 import (
    InstanceNotFoundError,
    InstanceNotReadyError,
    InstanceReadinessWaiter,
    InvalidInstanceIdError,
    detect_instance_platform,
    is_valid_instance_id,
)

logger = logging.getLogger(__name__)


class PlatformChoice(str, Enum):
    """Platform choice for EC2 instance OS."""

    AUTO = "auto"
    LINUX = "linux"
    WINDOWS = "windows"


def _validate_json_str(ctx: typer.Context, param: typer.CallbackParam, value: Optional[str]) -> Any:
    """Validate if the provided string is a valid JSON object string."""
    if value is None:
        return value

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as err:
        msg = "Failed to parse JSON argument"
        raise typer.BadParameter(msg, ctx, param) from err

    if not isinstance(parsed, dict):
        msg = "Parameters must be a JSON object (key-value mapping)"
        raise typer.BadParameter(msg, ctx, param)

    return value


@ec2_app.command()
def wait_for_ready(  # noqa: PLR0913
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
        min=1,
        help="Maximum number of attempts to check instance status.",
    ),
    delay: float = typer.Option(
        30.0,
        "--delay",
        min=0.0,
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

    Note:
    The target EC2 instance must have the AWS Systems Manager (SSM) Agent installed and running.
    It must also be attached to an IAM role/instance profile with sufficient SSM permissions
    (e.g., `AmazonSSMManagedInstanceCore`). Most standard AWS AMIs have the agent pre-installed.
    """
    # Check if the provided instance ID is valid
    if not is_valid_instance_id(instance_id):
        logger.error("Invalid EC2 instance ID '%s'", instance_id)
        raise typer.Exit(1)

    # Both document_name and document_parameters must be provided together
    if (document_name is None and document_parameters is not None) or (
        document_name is not None and document_parameters is None
    ):
        msg = "Both --document-name and --document-parameters must be provided together."
        raise typer.BadParameter(msg)

    # Determine the appropriate waiter based on platform choice or custom SSM document
    ssm_client = boto3.client("ssm")
    waiter: InstanceReadinessWaiter
    if document_name is not None and document_parameters is not None:
        parsed_parameters: dict[str, Any] = json.loads(document_parameters)
        waiter = InstanceReadinessWaiter(document_name, parsed_parameters, client=ssm_client)
    else:
        if platform == PlatformChoice.AUTO:
            ec2_client = boto3.client("ec2")
            try:
                response = ec2_client.describe_instances(InstanceIds=[instance_id])
                detected = detect_instance_platform(response, instance_id)
            except botocore.exceptions.ClientError as err:
                if err.response.get("Error", {}).get("Code") == "InvalidInstanceID.NotFound":
                    msg = f"Instance '{instance_id}' not found."
                    raise InstanceNotFoundError(msg) from err
                raise

            platform = PlatformChoice.WINDOWS if detected == "windows" else PlatformChoice.LINUX

        if platform == PlatformChoice.WINDOWS:
            waiter = InstanceReadinessWaiter(
                "AWS-RunPowerShellScript",
                {"commands": ["Write-Output 'ready'"]},
                client=ssm_client,
            )
        else:
            waiter = InstanceReadinessWaiter(
                "AWS-RunShellScript",
                {"commands": ["echo 'ready'"]},
                client=ssm_client,
            )

    # Start waiting for the instance to be ready using the selected waiter
    try:
        waiter.wait_for_ready(
            instance_id=instance_id,
            max_attempts=max_attempts,
            delay=delay,
        )
    except (InvalidInstanceIdError, InstanceNotFoundError, InstanceNotReadyError) as err:
        logger.error("Failed waiting for instance to be ready: %s", err)  # noqa: TRY400
        raise typer.Exit(1) from err

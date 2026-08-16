from __future__ import annotations

import logging
import time

import boto3
import typer

from aws_annoying.utils.ec2 import get_instance_id_by_name

from ._app import ec2_app

logger = logging.getLogger(__name__)


@ec2_app.command()
def wait_for_ready(
    ctx: typer.Context,
    *,
    instance: str = typer.Option(
        ...,
        show_default=False,
        help="The name or ID of the EC2 instance to wait for.",
    ),
    max_attempts: int = typer.Option(
        10,
        help="Maximum number of attempts to check instance status.",
    ),
    delay: float = typer.Option(
        30.0,
        help="Delay in seconds between attempts.",
    ),
) -> None:
    """Wait for an EC2 instance to be ready to accept SSM commands.

    Required IAM Permissions:

    - `ec2:DescribeInstances`
    - `ssm:SendCommand`
    - `ssm:GetCommandInvocation`
    """
    dry_run = ctx.meta.get("dry_run", False)

    instance_id = get_instance_id_by_name(instance)
    if not instance_id:
        logger.error("Instance '%s' not found.", instance)
        raise typer.Exit(1)

    logger.info("Waiting for instance [bold]%s[/bold] to be ready...", instance_id)
    if dry_run:
        logger.info("[dry-run] Would send SSM command to check readiness of %s.", instance_id)
        return

    ssm = boto3.client("ssm")

    for attempt in range(max_attempts):
        logger.info("Attempt %d/%d...", attempt + 1, max_attempts)
        try:
            res = ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName="AWS-RunShellScript",
                Parameters={"commands": ["echo 'ready' >> /tmp/ready.txt"]},
            )
            command_id = res["Command"]["CommandId"]
            time.sleep(5)
            inv = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id,
            )
            if inv.get("ResponseCode") == 0:
                logger.info("Instance [bold]%s[/bold] is ready.", instance_id)
                return
        except Exception as e:  # noqa: BLE001
            logger.debug("Attempt %d failed with error: %s", attempt + 1, e)

        if attempt < max_attempts - 1:
            time.sleep(delay)

    logger.error("Maximum attempts reached. Instance %s is not ready.", instance_id)
    raise typer.Exit(1)

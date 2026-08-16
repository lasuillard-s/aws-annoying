from __future__ import annotations

import logging
import os

import typer

from aws_annoying.cli.interactive import select_ec2_instance, select_ecs_container
from aws_annoying.cli.ui import prompt_select
from aws_annoying.session_manager import SessionManager
from aws_annoying.utils.ec2 import get_instance_id_by_name

from ._app import session_manager_app

logger = logging.getLogger(__name__)


@session_manager_app.command()
def start(
    ctx: typer.Context,
    *,
    target: str | None = typer.Option(
        None,
        help="The name or ID of the EC2 instance to connect to. If omitted, prompts interactively.",
    ),
    reason: str = typer.Option(
        "",
        help="The reason for starting the session.",
    ),
) -> None:
    """Start new session to your instance.

    You can use your EC2 instance identified by its name or ID. If there are
    more than one instance with the same name, the first one found will be used.

    Required IAM Permissions:

    - `ec2:DescribeInstances`
    - `ssm:StartSession`
    """
    dry_run = ctx.meta["dry_run"]
    session_manager = SessionManager()

    if target is None:
        target_type = prompt_select(
            "Target Type",
            choices=[
                ("ec2", "EC2 Instance"),
                ("ecs", "ECS Exec (Container)"),
            ],
        )
        if target_type == "ec2":
            target = select_ec2_instance()
        else:
            cluster, task, container = select_ecs_container()
            logger.info(
                "Starting ECS session to cluster=%s, task=%s, container=%s with reason: [italic]%r[/italic].",
                cluster,
                task,
                container,
                reason,
            )
            command = session_manager.build_ecs_command(
                cluster=cluster,
                task=task,
                container=container,
            )
            if not dry_run:
                os.execvp(command[0], command)  # noqa: S606
            return

    # EC2 logic
    # Resolve the instance name or ID
    instance_id = get_instance_id_by_name(target)
    if instance_id:
        logger.info("Instance ID resolved: [bold]%s[/bold]", instance_id)
        target = instance_id
    else:
        logger.info("Instance with name '%s' not found.", target)
        raise typer.Exit(1)

    # Start the session, replacing the current process
    logger.info(
        "Starting session to target [bold]%s[/bold] with reason: [italic]%r[/italic].",
        target,
        reason,
    )
    command = session_manager.build_command(
        target=target,
        document_name="SSM-SessionManagerRunShell",
        parameters={},
        reason=reason,
    )
    if not dry_run:
        os.execvp(command[0], command)  # noqa: S606

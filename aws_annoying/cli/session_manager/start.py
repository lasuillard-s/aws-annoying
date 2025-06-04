from __future__ import annotations

import logging
import os

import typer

from aws_annoying.utils.ec2 import get_instance_id_by_name

from ._app import session_manager_app
from ._common import SessionManager

logger = logging.getLogger(__name__)

# TODO(lasuillard): ECS support (#24)
# TODO(lasuillard): Interactive instance selection


@session_manager_app.command()
def start(
    ctx: typer.Context,
    *,
    target: str = typer.Option(
        ...,
        show_default=False,
        help="The name or ID of the EC2 instance to connect to.",
    ),
    reason: str = typer.Option(
        "",
        help="The reason for starting the session.",
    ),
) -> None:
    """Start new session."""
    dry_run = ctx.meta["dry_run"]
    session_manager = SessionManager()

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

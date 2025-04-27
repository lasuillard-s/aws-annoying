from __future__ import annotations

import os

import typer
from rich import print  # noqa: A004

from ._app import session_manager_app
from ._common import SessionManager, get_instance_id_by_name

# TODO(lasuillard): ECS support (#24)
# TODO(lasuillard): Interactive instance selection


@session_manager_app.command()
def start(
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
    session_manager = SessionManager()

    # Resolve the instance name or ID
    instance_id = get_instance_id_by_name(target)
    if instance_id:
        print(f"❗ Instance ID resolved: [bold]{instance_id}[/bold]")
        target = instance_id
    else:
        print(f"🚫 Instance with name '{target}' not found.")
        raise typer.Exit(1)

    # Start the session, replacing the current process
    print(f"🚀 Starting session to target [bold]{target}[/bold] with reason: [italic]{reason!r}[/italic].")
    command = session_manager.build_command(
        target=target,
        document_name="SSM-SessionManagerRunShell",
        parameters={},
        reason=reason,
    )
    os.execvp(command[0], command)  # noqa: S606

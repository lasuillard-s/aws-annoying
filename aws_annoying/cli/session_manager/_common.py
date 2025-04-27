# TODO(lasuillard): Using this file until split CLI from library codebase
from __future__ import annotations

import re
from typing import Any

import boto3
import typer
from rich.prompt import Confirm

from aws_annoying.session_manager import SessionManager as _SessionManager


# Custom session manager with console interactivity
class SessionManager(_SessionManager):
    def before_install(self, command: list[str]) -> None:
        if self._confirm:
            return

        confirm = Confirm.ask(f"⚠️ Will run the following command: [bold red]{' '.join(command)}[/bold red]. Proceed?")
        if not confirm:
            raise typer.Abort

    def install(self, *args: Any, confirm: bool = False, **kwargs: Any) -> None:
        self._confirm = confirm
        return super().install(*args, **kwargs)


def get_instance_id_by_name(name_or_id: str) -> str | None:
    """Get the EC2 instance ID by name or ID.

    Be aware that this function will only return the first instance found
    with the given name, no matter how many instances are found.

    Args:
        name_or_id: The name or ID of the EC2 instance.

    Returns:
        The instance ID if found, otherwise `None`.
    """
    if re.match(r"m?i-.+", name_or_id):
        return name_or_id

    ec2 = boto3.client("ec2")
    response = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [name_or_id]}])
    reservations = response["Reservations"]
    if not reservations:
        return None

    instances = reservations[0]["Instances"]
    if not instances:
        return None

    return str(instances[0]["InstanceId"])

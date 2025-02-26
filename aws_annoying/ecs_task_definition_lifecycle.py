from __future__ import annotations

import boto3
import typer
from rich import print  # noqa: A004

from .app import app


@app.command()
def ecs_task_definition_lifecycle(
    *,
    family: str = typer.Option(
        ...,
        help="The name of the task definition family.",
        show_default=False,
    ),
    keep_latest: int = typer.Option(
        ...,
        help="Number of latest (revision) task definitions to keep.",
        show_default=False,
        min=1,
        max=100,
    ),
) -> None:
    """Execute ECS task definition lifecycle."""
    ecs = boto3.client("ecs")
    task_definitions = ecs.list_task_definitions(familyPrefix=family, status="ACTIVE")
    expired_defs = task_definitions["taskDefinitionArns"][:-keep_latest]
    for arn in expired_defs:
        ecs.deregister_task_definition(taskDefinition=arn)
        print(f"✅ Deregistered task definition [yellow]{arn!r}[/yellow]")

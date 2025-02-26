from __future__ import annotations

from rich import print  # noqa: A004

from .app import app


@app.command()
def ecs_task_definition_lifecycle() -> None:
    """Execute ECS task definition lifecycle."""
    print("Handling ECS task definition lifecycle...")

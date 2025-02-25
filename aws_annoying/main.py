from __future__ import annotations

import typer

from aws_annoying.utils.debugger import input_as_args

from .ecs_task_definition_lifecycle import ecs_task_definition_lifecycle
from .load_variables import load_variables

app = typer.Typer()

app.command()(ecs_task_definition_lifecycle)
app.command()(load_variables)


def entrypoint() -> None:  # noqa: D103  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    with input_as_args():
        entrypoint()

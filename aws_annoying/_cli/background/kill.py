from __future__ import annotations

import logging
from pathlib import Path

import typer

from ._app import background_app
from ._process import terminate_process_by_pid_file

logger = logging.getLogger(__name__)


@background_app.command()
def kill(
    *,
    pid_file: Path = typer.Option(  # noqa: B008
        Path("./.aws-annoying.pid"),
        help="The path to the PID file of the background process to terminate.",
    ),
    remove: bool = typer.Option(
        True,  # noqa: FBT003
        help="Remove the PID file after terminating the process.",
    ),
) -> None:
    """Terminate running background process for PID file."""
    # Check if PID file exists
    if not pid_file.is_file():
        logger.error("PID file not found: %s", pid_file)
        raise typer.Exit(1)

    terminate_process_by_pid_file(pid_file, remove=remove)
    logger.info("Terminated the background process successfully.")

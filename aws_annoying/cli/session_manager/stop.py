from __future__ import annotations

import logging
import os
import signal
from pathlib import Path  # noqa: TC003

import typer

from ._app import session_manager_app

logger = logging.getLogger(__name__)


@session_manager_app.command()
def stop(
    pid_file: Path = typer.Option(  # noqa: B008
        "./session-manager-plugin.pid",
        help="The path to the PID file to store the process ID of the session manager plugin.",
    ),
    remove: bool = typer.Option(  # noqa: FBT001
        True,  # noqa: FBT003
        help="Remove the PID file after stopping the session.",
    ),
) -> None:
    """Stop running session for PID file."""
    # Check if PID file exists
    if not pid_file.is_file():
        logger.error("❌ PID file not found: %s", pid_file)
        raise typer.Exit(1)

    # Read PID from file
    pid_content = pid_file.read_text()
    try:
        pid = int(pid_content)
    except ValueError:
        logger.error("🚫 PID file content is invalid; expected integer, but got: %s", type(pid_content))  # noqa: TRY400
        raise typer.Exit(1) from None

    # Send SIGTERM to the process
    try:
        logger.warning("⚠️ Terminating running process with PID %d.", pid)
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        logger.warning("❗ Tried to terminate process with PID %d but does not exist.", pid)

    # Remove the PID file
    if remove:
        logger.info("✅ Removed the PID file %s.", pid_file)
        pid_file.unlink()

    logger.info("✅ Terminated the session successfully.")

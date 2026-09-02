from __future__ import annotations

import logging
import os
import signal
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def terminate_process_by_pid_file(
    pid_file: Path,
    *,
    remove: bool = False,
) -> None:
    """Terminate the process recorded in the given PID file.

    Args:
        pid_file: Path to the PID file.
        remove: If True, remove the PID file after termination.
    """
    pid_content = pid_file.read_text().strip()
    if not pid_content:
        if remove:
            logger.info("Removed the PID file %s.", pid_file)
            pid_file.unlink()

        return

    try:
        pid = int(pid_content)
    except ValueError:
        logger.error("PID file content is invalid; expected integer, but got: %r", pid_content)  # noqa: TRY400
        raise typer.Exit(1) from None

    if pid <= 0:
        logger.error("PID must be strictly positive, but got: %d", pid)
        raise typer.Exit(1)

    try:
        logger.warning("Terminating running process with PID %d.", pid)
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        logger.warning("Tried to terminate process with PID %d but does not exist.", pid)

    if remove:
        logger.info("Removed the PID file %s.", pid_file)
        pid_file.unlink()

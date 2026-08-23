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
    dry_run: bool = False,
    remove: bool = False,
    clear: bool = False,
) -> None:
    """Terminate the process recorded in the given PID file.

    Args:
        pid_file: Path to the PID file.
        dry_run: If True, do not actually terminate the process or modify files.
        remove: If True, remove the PID file after termination.
        clear: If True, clear the content of the PID file after termination.
    """
    pid_content = pid_file.read_text().strip()
    if not pid_content:
        return

    try:
        pid = int(pid_content)
    except ValueError:
        logger.error("PID file content is invalid; expected integer, but got: %r", pid_content)  # noqa: TRY400
        raise typer.Exit(1) from None

    try:
        logger.warning("Terminating running process with PID %d.", pid)
        if not dry_run:
            os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        logger.warning("Tried to terminate process with PID %d but does not exist.", pid)
    finally:
        if clear:
            pid_file.write_text("")

    if remove:
        logger.info("Removed the PID file %s.", pid_file)
        if not dry_run:
            pid_file.unlink()

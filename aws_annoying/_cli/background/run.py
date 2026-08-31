from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import typer

from aws_annoying.utils.platform import is_windows

from ._app import background_app
from ._process import terminate_process_by_pid_file

logger = logging.getLogger(__name__)


@background_app.command(
    context_settings={
        # Allow extra arguments for user provided command
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    }
)
def run(
    ctx: typer.Context,
    *,
    pid_file: Path = typer.Option(  # noqa: B008
        Path("./.aws-annoying.pid"),
        help="The path to the PID file to store the process ID of the background command.",
    ),
    terminate_running_process: bool = typer.Option(
        False,  # noqa: FBT003
        help="Terminate the process in the PID file if it already exists.",
    ),
    log_file: Path = typer.Option(  # noqa: B008
        Path("./.aws-annoying.log"),
        help="The path to the log file to store the output of the background command.",
    ),
) -> None:
    r"""Run a command in the background detached from the current terminal.

    Examples:
        - Run a port-forwarding command in the background and store its PID in a file:

            ```bash
            $ aws-annoying background run \
                --pid-file ./session.pid \
                --terminate-running-process \
                -- session-manager port-forward \
                    ...
            ```
    """
    command = ctx.args

    if not command:
        logger.error("No command specified to run in the background.")
        raise typer.Exit(1)

    # NOTE: This(background run) is a wrapper around the main CLI command
    command = [sys.executable, "-m", "aws_annoying._cli.main", *command]

    # Handle existing PID file if specified
    if pid_file.exists():
        if not terminate_running_process:
            logger.error("PID file already exists: %s", pid_file)
            raise typer.Exit(1)

        terminate_process_by_pid_file(pid_file, remove=True)

    stdout = log_file.open(mode="at+", buffering=1)
    logger.info("Starting background process: %s", " ".join(command))
    pid = _spawn_process(command, stdout)
    if hasattr(stdout, "close"):
        stdout.close()

    logger.info("Process started with PID %d. Outputs will be logged to %s.", pid, log_file.absolute())
    pid_file.write_text(str(pid))
    logger.info("PID file written to %s.", pid_file.absolute())


def _spawn_process(command: list[str], stdout: subprocess._FILE) -> int:
    if is_windows():
        proc = subprocess.Popen(  # noqa: S603
            command,
            stdout=stdout,
            stderr=subprocess.STDOUT,
            text=True,
            close_fds=False,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,  # type: ignore[attr-defined]
        )
    else:
        proc = subprocess.Popen(  # noqa: S603
            command,
            stdout=stdout,
            stderr=subprocess.STDOUT,
            text=True,
            close_fds=False,
            start_new_session=True,
        )
    return proc.pid

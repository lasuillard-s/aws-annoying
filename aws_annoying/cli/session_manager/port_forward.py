from __future__ import annotations

import logging
import os
import signal
import socket
import subprocess
import sys
from pathlib import Path  # noqa: TC003

import typer

from aws_annoying.session_manager import SessionManager
from aws_annoying.utils.ec2 import get_instance_id_by_name

from ._app import session_manager_app

logger = logging.getLogger(__name__)


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _handle_existing_pid_file(pid_file: Path, terminate_running_process: bool) -> None:  # noqa: FBT001
    if not pid_file.exists():
        return

    if not terminate_running_process:
        logger.error("PID file already exists.")
        raise typer.Exit(1)

    pid_content = pid_file.read_text().strip()
    if pid_content:
        for pid_str in pid_content.split():
            try:
                existing_pid = int(pid_str)
                logger.warning("Terminating running process with PID %d.", existing_pid)
                os.kill(existing_pid, signal.SIGTERM)
            except (ValueError, ProcessLookupError):  # noqa: PERF203
                logger.warning("Tried to terminate process with PID %s but failed.", pid_str)
        pid_file.write_text("")  # Clear the PID file


# https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html
@session_manager_app.command()
def port_forward(  # noqa: PLR0913
    ctx: typer.Context,
    *,
    local_host: str = typer.Option(
        "127.0.0.1",
        help="The local host address to bind the port forwarding connection.",
    ),
    local_port: int = typer.Option(
        ...,
        show_default=False,
        help="The local port to use for port forwarding.",
    ),
    through: str = typer.Option(
        ...,
        show_default=False,
        help="The name or ID of the EC2 instance to use as a proxy for port forwarding.",
    ),
    remote_host: str = typer.Option(
        ...,
        show_default=False,
        help="The remote host to connect to.",
    ),
    remote_port: int = typer.Option(
        ...,
        show_default=False,
        help="The remote port to connect to.",
    ),
    reason: str = typer.Option(
        "",
        help="The reason for starting the port forwarding session.",
    ),
    pid_file: Path = typer.Option(  # noqa: B008
        "./session-manager-plugin.pid",
        help="The path to the PID file to store the process ID of the session manager plugin.",
    ),
    terminate_running_process: bool = typer.Option(
        False,  # noqa: FBT003
        help="Terminate the process in the PID file if it already exists.",
    ),
    log_file: Path = typer.Option(  # noqa: B008
        "./session-manager-plugin.log",
        help="The path to the log file to store the output of the session manager plugin.",
    ),
) -> None:
    """Start a port forwarding session using AWS Session Manager.

    This command allows starting a port forwarding session through an EC2 instance identified by its name or ID.
    If there are more than one instance with the same name, the first one found will be used.

    Also, it manages a PID file to keep track of the session manager plugin process running in background,
    allowing to terminate any existing process before starting a new one.

    Required IAM Permissions:

    - `ec2:DescribeInstances`
    - `ssm:StartSession`
    """
    dry_run = ctx.meta["dry_run"]
    session_manager = SessionManager()

    _handle_existing_pid_file(pid_file, terminate_running_process)

    # Resolve the instance name or ID
    instance_id = get_instance_id_by_name(through)
    if instance_id:
        logger.info("Instance ID resolved: [bold]%s[/bold]", instance_id)
        target = instance_id
    else:
        logger.error("Instance with name '%s' not found.", through)
        raise typer.Exit(1)

    is_non_localhost = local_host not in ("127.0.0.1", "localhost")
    ssm_local_port = _get_free_port() if is_non_localhost else local_port

    # Initiate the session
    command = session_manager.build_command(
        target=target,
        document_name="AWS-StartPortForwardingSessionToRemoteHost",
        parameters={
            "host": [remote_host],
            "portNumber": [str(remote_port)],
            "localPortNumber": [str(ssm_local_port)],
        },
        reason=reason,
    )
    stdout: subprocess._FILE
    if log_file is not None:  # noqa: SIM108
        stdout = log_file.open(mode="at+", buffering=1)
    else:
        stdout = subprocess.DEVNULL

    logger.info(
        "Starting port forwarding session through [bold]%s[/bold] with reason: [italic]%r[/italic].",
        through,
        reason,
    )
    pids: list[int] = []
    if not dry_run:
        proc = subprocess.Popen(  # noqa: S603
            command,
            stdout=stdout,
            stderr=subprocess.STDOUT,
            text=True,
            close_fds=False,  # FD inherited from parent process
        )
        pids.append(proc.pid)

        if is_non_localhost:
            proxy_cmd = [
                sys.executable,
                "-m",
                "aws_annoying.utils.tcp_proxy",
                local_host,
                str(local_port),
                "127.0.0.1",
                str(ssm_local_port),
            ]
            proxy_proc = subprocess.Popen(proxy_cmd)  # noqa: S603
            pids.append(proxy_proc.pid)
            logger.info("TCP Proxy started on %s:%d -> 127.0.0.1:%d", local_host, local_port, ssm_local_port)
    else:
        pids.append(-1)

    logger.info(
        "Session Manager Plugin started with PID %s. Outputs will be logged to %s.",
        ", ".join(map(str, pids)),
        log_file.absolute(),
    )

    # Write the PID to the file
    if not dry_run:
        pid_file.write_text(" ".join(map(str, pids)))

    logger.info("PID file written to %s.", pid_file.absolute())

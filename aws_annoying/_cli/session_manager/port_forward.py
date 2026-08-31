from __future__ import annotations

import logging
import signal
import subprocess
from typing import Any

import typer

from aws_annoying.ec2 import get_instance_id_by_name
from aws_annoying.session_manager import SessionManager
from aws_annoying.utils.network import get_free_port
from aws_annoying.utils.tcp_proxy import TCPProxy

from ._app import session_manager_app

logger = logging.getLogger(__name__)


# https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html
@session_manager_app.command()
def port_forward(  # noqa: PLR0913
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
) -> None:
    """Start a port forwarding session using AWS Session Manager.

    This command allows starting a port forwarding session through an EC2 instance identified by its name or ID.
    If there are more than one instance with the same name, the first one found will be used.

    Required IAM Permissions:

    - `ec2:DescribeInstances`
    - `ssm:StartSession`
    """
    session_manager = SessionManager()

    # Resolve the instance name or ID
    instance_id = get_instance_id_by_name(through)
    if instance_id:
        logger.info("Instance ID resolved: [bold]%s[/bold]", instance_id)
        target = instance_id
    else:
        logger.error("Instance with name '%s' not found.", through)
        raise typer.Exit(1)

    is_non_localhost = local_host not in ("127.0.0.1", "localhost")
    ssm_local_host = "127.0.0.1"
    ssm_local_port = get_free_port() if is_non_localhost else local_port

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

    logger.info(
        "Starting port forwarding session through [bold]%s[/bold] with reason: [italic]%r[/italic].",
        through,
        reason,
    )

    proxy: TCPProxy | None = None
    if is_non_localhost:
        proxy = TCPProxy(local_host, local_port, ssm_local_host, ssm_local_port)
        proxy.start()
        logger.info(
            "TCP Proxy started on %s:%d -> %s:%d",
            local_host,
            local_port,
            ssm_local_host,
            ssm_local_port,
        )

    # NOTE: stdout=None inherits the parent process's standard output stream without
    #       requiring a concrete file descriptor (sys.stdout.fileno()), preventing errors in
    #       environments where stdout is captured (e.g. pytest or CLI test runners).
    proc = subprocess.Popen(  # noqa: S603
        command,
        stdout=None,
        stderr=subprocess.STDOUT,
        text=True,
    )

    def handle_signal(sig: int, _frame: Any) -> None:
        logger.info("Received signal %d, stopping port forwarding...", sig)
        proc.terminate()
        if proxy is not None:
            proxy.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        return_code = proc.wait()
    finally:
        if proxy is not None:
            proxy.stop()

    if return_code != 0:
        raise typer.Exit(return_code)

from __future__ import annotations

import logging
import subprocess
from contextlib import contextmanager
from typing import TYPE_CHECKING

from aws_annoying.utils.timeout import Timeout

from .session_manager import SessionManager

if TYPE_CHECKING:
    from collections.abc import Iterator


logger = logging.getLogger(__name__)


@contextmanager
def port_forward(  # noqa: PLR0913
    *,
    through: str,
    local_port: int,
    remote_host: str,
    remote_port: int,
    reason: str | None = None,
    start_timeout: int | None = None,
) -> Iterator[subprocess.Popen[str]]:
    """Context manager for port forwarding sessions.

    Args:
        through: The instance ID to use as port-forwarding proxy.
        local_port: The local port to listen to.
        remote_host: The remote host to connect to.
        remote_port: The remote port to connect to.
        reason: The reason for starting the session.
        start_timeout: The timeout in seconds to wait for the session to start.

    Returns:
        The command to start the session.
    """
    session_manager = SessionManager()
    command = session_manager.build_command(
        target=through,
        document_name="AWS-StartPortForwardingSessionToRemoteHost",
        parameters={
            "localPortNumber": [str(local_port)],
            "host": [remote_host],
            "portNumber": [str(remote_port)],
        },
        reason=reason,
    )
    try:
        proc = subprocess.Popen(  # noqa: S603
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # * Must be unreachable
        if proc.stdout is None:
            msg = "Standard output is not available"
            raise RuntimeError(msg)

        # Wait for the session to start
        # ? Not sure this is trustworthy health check
        with Timeout(start_timeout):
            for line in proc.stdout:
                if "Waiting for connections..." in line:
                    logger.info("Session started successfully.")
                    break

        yield proc
    finally:
        proc.terminate()

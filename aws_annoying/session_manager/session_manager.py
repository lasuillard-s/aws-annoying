from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import boto3

from aws_annoying.utils.platform import is_windows

from .errors import PluginNotInstalledError

logger = logging.getLogger(__name__)


class SessionManager:
    """AWS Session Manager plugin manager."""

    def __init__(self, *, session: boto3.session.Session | None = None) -> None:
        """Initialize SessionManager.

        Args:
            session: Boto3 session to use for AWS operations.
        """
        self.session = session or boto3.session.Session()

    def verify_installation(self) -> tuple[bool, Path | None, str | None]:
        """Verify installation of AWS Session Manager plugin.

        Returns:
            3-tuple of boolean flag indicating whether plugin installed, binary path and version string.
        """
        # Find plugin binary
        if not (binary_path := self._get_binary_path()):
            return False, None, None

        # Check version
        result_bytes = subprocess.run(  # noqa: S603
            [str(binary_path), "--version"],
            check=True,
            capture_output=True,
        )
        result = result_bytes.stdout.decode().strip()
        if not bool(re.match(r"[\d\.]+", result)):
            return False, binary_path, result

        return True, binary_path, result

    def _get_binary_path(self) -> Path | None:
        """Get the path to the session-manager-plugin binary."""
        binary_path_str = shutil.which("session-manager-plugin")
        if not binary_path_str:
            if is_windows():
                # Windows: use the default installation path
                binary_path = (
                    Path(os.environ["ProgramFiles"])  # noqa: SIM112
                    / "Amazon"
                    / "SessionManagerPlugin"
                    / "bin"
                    / "session-manager-plugin.exe"
                )
                if binary_path.is_file():
                    return binary_path.absolute()

            return None

        return Path(binary_path_str).absolute()

    # ------------------------------------------------------------------------
    # Command
    # ------------------------------------------------------------------------
    def build_command(
        self,
        target: str,
        document_name: str,
        parameters: dict[str, Any],
        reason: str | None = None,
    ) -> list[str]:
        """Build command for starting a session.

        Args:
            target: The target instance ID.
            document_name: The SSM document name to use for the session.
            parameters: The parameters to pass to the SSM document.
            reason: The reason for starting the session.

        Returns:
            The command to start the session.
        """
        is_installed, binary_path, _version = self.verify_installation()
        if not is_installed:
            msg = "Session Manager plugin is not installed."
            raise PluginNotInstalledError(msg)

        ssm = self.session.client("ssm")
        response = ssm.start_session(
            Target=target,
            DocumentName=document_name,
            Parameters=parameters,
            # ? Reason is optional but it doesn't allow empty string or `None`
            **({"Reason": reason} if reason else {}),
        )

        region = self.session.region_name
        return [
            str(binary_path),
            json.dumps(response),
            region,
            "StartSession",
            self.session.profile_name,
            json.dumps({"Target": target}),
            f"https://ssm.{region}.amazonaws.com",
        ]

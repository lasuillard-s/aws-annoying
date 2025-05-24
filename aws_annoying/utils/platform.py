from __future__ import annotations

import os
import platform
from pathlib import Path


def command_as_root(command: list[str], *, root: bool | None = None) -> list[str]:
    """Modify a command to run as root (`sudo`) if not already running as root."""
    root = root or is_root()
    if not root:
        command = ["sudo", *command]

    return command


def is_root() -> bool:
    """Check if the current user is root."""
    return os.geteuid() == 0


def os_release() -> dict[str, str]:
    """Parse `/etc/os-release` file into a dictionary."""
    content = Path("/etc/os-release").read_text()
    return {
        key.strip('"'): value.strip('"')
        for key, value in (line.split("=", 1) for line in content.splitlines() if "=" in line)
    }


def is_macos() -> bool:
    """Check if the current OS is macOS."""
    return platform.system() == "Darwin"


def is_windows() -> bool:
    """Check if the current OS is Windows."""
    return platform.system() == "Windows"

from __future__ import annotations

import os


def command_as_root(command: list[str], *, root: bool | None = None) -> list[str]:
    """Modify a command to run as root (`sudo`) if not already running as root."""
    root = root or is_root()
    if not root:
        command = ["sudo", *command]

    return command


def is_root() -> bool:
    """Check if the current user is root."""
    return os.geteuid() == 0

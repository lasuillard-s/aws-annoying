# ruff: noqa: F401
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import app

try:
    import aws_annoying._cli.ecs
    import aws_annoying._cli.load_variables
    import aws_annoying._cli.mfa
    import aws_annoying._cli.session_manager

    from .app import app
except ImportError:
    app = None  # type: ignore[assignment]

__all__ = ("app", "entrypoint")


def entrypoint() -> None:
    """Run the CLI application or exit with an error message if CLI dependencies are not installed."""
    if app is None:
        sys.exit("Error: CLI dependencies are missing. Please install or run with the 'cli' extra.")
    app()


if __name__ == "__main__":  # pragma: no cover
    from aws_annoying.utils.debugger import input_as_args

    with input_as_args():
        entrypoint()

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import app

try:
    import typer  # noqa: F401
except ImportError:
    app = None  # type: ignore[assignment]
else:
    from . import background as _background  # noqa: F401
    from . import ec2 as _ec2  # noqa: F401
    from . import ecs as _ecs  # noqa: F401
    from . import load_variables as _load_variables  # noqa: F401
    from . import mfa as _mfa  # noqa: F401
    from . import session_manager as _session_manager  # noqa: F401
    from .app import app

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

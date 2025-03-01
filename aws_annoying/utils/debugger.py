from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator


# https://stackoverflow.com/questions/38634988/check-if-program-runs-in-debug-mode
def is_debugger_active() -> bool:  # pragma: no cover
    """Return if debugger is active."""
    return hasattr(sys, "gettrace") and sys.gettrace() is not None


@contextmanager
def input_as_args() -> Generator[None, None, None]:  # pragma: no cover
    """Context manager modifying `sys.argv` to pass CLI arguments via input while using debugger."""
    if is_debugger_active():
        args = input("Arguments: ")
        if args:
            sys.argv.extend(args.split(" "))

    yield

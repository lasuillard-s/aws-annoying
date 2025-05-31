from __future__ import annotations

import signal
from functools import wraps
from typing import TYPE_CHECKING, Callable, TypeVar, cast

from aws_annoying.utils.platform import is_windows

if TYPE_CHECKING:
    from types import FrameType
    from typing import Any


class OperationTimeoutError(Exception):
    """Operation timed out."""


_F = TypeVar("_F", bound=Callable)


class Timeout:
    """Timeout handler utilizing signals.

    This utility relies on Unix signals (`signal.SIGALRM`). The behavior will be dummied
    to do nothing on Windows OS.
    """

    def __init__(self, seconds: int | None) -> None:
        """Initialize timeout handler.

        Args:
            seconds: The timeout in seconds. `None` means no timeout,
                allowing the function to run normally.

        """
        self.timeout_seconds = seconds

        self._signal_handler_registered = False

    def _set_signal_handler(self) -> None:
        if is_windows() or self.timeout_seconds is None:
            return

        signal.signal(signal.SIGALRM, self._handler)
        signal.alarm(self.timeout_seconds)
        self._signal_handler_registered = True

    def _handler(self, signum: int, frame: FrameType | None) -> Any:  # noqa: ARG002
        msg = "Timeout reached"
        raise OperationTimeoutError(msg)

    def _reset_signal_handler(self) -> None:
        if is_windows() or not self._signal_handler_registered:
            return

        signal.signal(signal.SIGALRM, signal.SIG_IGN)
        signal.alarm(0)
        self._signal_handler_registered = False

    def __call__(self, func: _F) -> _F:
        """Decorator to set a timeout for a function.

        Please note, using this decorator in nested functions may not work properly as
        the signal handler for outer functions may not be resumed correctly.

        Raises:
            OperationTimeoutError: When timeout is reached.
        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self._set_signal_handler()
            try:
                return func(*args, **kwargs)
            finally:
                self._reset_signal_handler()

        return cast("_F", wrapper)

    def __enter__(self) -> None:
        self._set_signal_handler()

    def __exit__(self, *args: object) -> Any:
        self._reset_signal_handler()
        return False  # Re-raise

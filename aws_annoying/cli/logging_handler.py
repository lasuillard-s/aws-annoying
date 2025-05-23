from __future__ import annotations

import logging
import logging.config
from typing import TYPE_CHECKING, Any

from typing_extensions import override

if TYPE_CHECKING:
    from rich.console import Console


# TODO(lasuillard): Add emoji formatting support
class RichLogHandler(logging.Handler):
    """Custom logging handler to use Rich Console."""

    def __init__(self, console: Console, *args: Any, **kwargs: Any) -> None:
        """Initialize the log handler.

        Args:
            console: Rich console instance.
            *args: Additional arguments for the logging handler.
            **kwargs: Additional keyword arguments for the logging handler.
        """
        super().__init__(*args, **kwargs)
        self.console = console

    @override
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.console.print(msg)

import logging
import logging.config
from typing import Any, Final

from rich.console import Console
from typing_extensions import override


class RichLogHandler(logging.Handler):
    """Custom logging handler to use Rich Console."""

    _level_emojis: Final[dict[str, str]] = {
        "DEBUG": "🔍",
        "INFO": "🔔",
        "WARNING": "⚠️",
        "ERROR": "🚨",
        "CRITICAL": "🔥",
    }

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

    @override
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record.

        Args:
            record: The log record to format.

        Returns:
            The formatted log message.
        """
        msg = super().format(record)
        emoji = self._level_emojis.get(record.levelname)
        return f"{emoji} {msg}" if emoji else msg

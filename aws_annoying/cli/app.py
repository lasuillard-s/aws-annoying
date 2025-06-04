from __future__ import annotations

import importlib.metadata
import logging
import logging.config
from typing import Optional

import typer
from rich import print  # noqa: A004
from rich.console import Console
from rich.highlighter import ReprHighlighter
from rich.theme import Theme

logger = logging.getLogger(__name__)

app = typer.Typer(
    pretty_exceptions_short=True,
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def show_version(value: Optional[bool]) -> None:
    """Show the version of the application."""
    if not value:
        return

    print(importlib.metadata.version("aws-annoying"))
    raise typer.Exit(0)


@app.callback()
def main(  # noqa: D103
    ctx: typer.Context,
    *,
    version: Optional[bool] = typer.Option(  # noqa: ARG001
        None,
        "--version",
        is_eager=True,
        callback=show_version,
        help="Show the version and exit.",
    ),
    quiet: bool = typer.Option(
        False,  # noqa: FBT003
        help="Disable outputs.",
    ),
    verbose: bool = typer.Option(
        False,  # noqa: FBT003
        help="Enable verbose outputs.",
    ),
    dry_run: bool = typer.Option(
        False,  # noqa: FBT003
        help="Enable dry-run mode. If enabled, certain commands will avoid making changes.",
    ),
) -> None:
    log_level = logging.DEBUG if verbose else logging.INFO
    console = _get_console()
    logging_config: logging.config._DictConfigArgs = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "rich": {
                "format": "%(message)s",
                "datefmt": "[%X]",
            },
        },
        "handlers": {
            "null": {
                "class": "logging.NullHandler",
            },
            "rich": {
                "class": "aws_annoying.cli.logging_handler.RichLogHandler",
                "formatter": "rich",
                "console": console,
            },
        },
        "root": {
            "handlers": ["null"],
        },
        "loggers": {
            "aws_annoying": {
                "level": log_level,
                "handlers": ["rich"],
                "propagate": True,
            },
        },
    }
    if quiet:
        logging_config["loggers"]["aws_annoying"]["level"] = logging.CRITICAL

    logging.config.dictConfig(logging_config)

    # Global flags
    ctx.meta["dry_run"] = dry_run
    if dry_run:
        logger.warning("Dry run mode enabled. Some operation may behave differently to avoid making changes.")


def _get_console() -> Console:
    theme = Theme(
        {
            "repr.arn": "bold orange3",
            "repr.constant": "bold blue",
        },
    )
    return Console(soft_wrap=True, emoji=False, highlighter=CustomHighlighter(), theme=theme)


class CustomHighlighter(ReprHighlighter):
    """Custom highlighter to handle additional patterns."""

    highlights = [  # noqa: RUF012
        *ReprHighlighter.highlights,
        # AWS Resource Name; https://docs.aws.amazon.com/IAM/latest/UserGuide/reference-arns.html
        # NOTE: Quite simplified regex, may not cover all cases.
        r"(?P<arn>\barn:[0-9a-zA-Z/+=,\.@_\-:]+\b)",
        # Constants
        r"(?P<constant>\b[A-Z_]+\b)",
    ]

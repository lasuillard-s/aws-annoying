from __future__ import annotations

import logging
import logging.config

import typer

app = typer.Typer(
    pretty_exceptions_short=True,
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.callback()
def main(  # noqa: D103
    *,
    quiet: bool = typer.Option(
        False,  # noqa: FBT003
        help="Disable outputs.",
    ),
    verbosity: int = typer.Option(
        0,
        "--verbose",  # `--verbose --verbose --verbose` equals to `-vvv`, but normally won't be used
        "-v",
        count=True,
        help="Increase verbosity level. Use `-vvv` for full output.",
        min=0,
        max=3,
        show_default=False,
    ),
) -> None:
    log_level = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG, 3: logging.NOTSET}[verbosity]
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
                "class": "rich.logging.RichHandler",
                "formatter": "rich",
                "show_time": False,
                "show_level": False,
                "markup": True,
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
        del logging_config["loggers"]["aws_annoying"]

    logging.config.dictConfig(logging_config)

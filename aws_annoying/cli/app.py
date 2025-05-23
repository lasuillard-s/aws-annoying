from __future__ import annotations

import logging

import typer
from rich.logging import RichHandler

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
        "--quiet",
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
    if not quiet:
        log_level = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG, 3: logging.NOTSET}.get(verbosity)
        logging.basicConfig(
            level=log_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[
                # Reproduce `rich.print` behavior
                RichHandler(show_time=False, show_level=False, markup=True),
            ],
        )

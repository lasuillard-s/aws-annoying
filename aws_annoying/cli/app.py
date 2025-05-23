from __future__ import annotations

from typing import TypedDict

import typer

app = typer.Typer(
    pretty_exceptions_short=True,
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)


class GlobalFlags(TypedDict):
    """CLI global flags."""

    dry_run: bool


global_flags = GlobalFlags(
    dry_run=False,
)


@app.callback()
def main(  # noqa: D103
    *,
    dry_run: bool = typer.Option(
        False,  # noqa: FBT003
        help="Enable dry-run mode. If enabled, certain commands will avoid making changes.",
    ),
) -> None:
    global_flags["dry_run"] = dry_run

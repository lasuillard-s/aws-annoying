from __future__ import annotations

import typer

app = typer.Typer(
    pretty_exceptions_short=True,
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.callback()
def main(  # noqa: D103
    ctx: typer.Context,
    *,
    dry_run: bool = typer.Option(
        False,  # noqa: FBT003
        help="Enable dry-run mode. If enabled, certain commands will avoid making changes.",
    ),
) -> None:
    ctx.meta["dry_run"] = dry_run

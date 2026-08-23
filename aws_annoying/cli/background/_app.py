import typer

from aws_annoying.cli.app import app

background_app = typer.Typer(
    no_args_is_help=True,
    help="Background process management commands.",
)
app.add_typer(background_app, name="background")

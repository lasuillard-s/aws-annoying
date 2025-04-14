import typer

from aws_annoying.cli.app import app

mfa_app = typer.Typer(
    no_args_is_help=True,
    help="Commands to manage MFA authentication.",
)
app.add_typer(mfa_app, name="mfa")

import typer

from aws_annoying._cli.app import app

ec2_app = typer.Typer(
    no_args_is_help=True,
    help="EC2 (Elastic Compute Cloud) utility commands.",
)
app.add_typer(ec2_app, name="ec2")

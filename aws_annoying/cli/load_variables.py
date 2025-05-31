# flake8: noqa: B008
from __future__ import annotations

import logging
import os
import subprocess
from io import StringIO
from typing import NoReturn, Optional

import typer
from rich.console import Console
from rich.table import Table

from aws_annoying.variable_loader import VariableLoader

from .app import app

logger = logging.getLogger(__name__)


@app.command(
    context_settings={
        # Allow extra arguments for user provided command
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
)
def load_variables(
    ctx: typer.Context,
    *,
    arns: list[str] = typer.Option(
        [],
        metavar="ARN",
        help=(
            "ARNs of the secret or parameter to load."
            " The variables are loaded in the order of the ARNs,"
            " overwriting the variables with the same name in the order of the ARNs."
        ),
    ),
    env_prefix: Optional[str] = typer.Option(
        None,
        help="Prefix of the environment variables to load the ARNs from.",
        show_default=False,
    ),
    overwrite_env: bool = typer.Option(
        False,  # noqa: FBT003
        help="Overwrite the existing environment variables with the same name.",
    ),
    replace: bool = typer.Option(
        True,  # noqa: FBT003
        help=(
            "Replace the current process (`os.execvpe`) with the command."
            " If disabled, run the command as a `subprocess`."
        ),
    ),
) -> NoReturn:
    """Wrapper command to run command with variables from AWS resources injected as environment variables.

    This script is intended to be used in the ECS environment, where currently AWS does not support
    injecting whole JSON dictionary of secrets or parameters as environment variables directly.

    It first loads the variables from the AWS sources then runs the command with the variables injected as environment variables.

    In addition to `--arns` option, you can provide ARNs as the environment variables by providing `--env-prefix`.
    For example, if you have the following environment variables:

    ```shell
    export LOAD_AWS_CONFIG__001_app_config=arn:aws:secretsmanager:...
    export LOAD_AWS_CONFIG__002_db_config=arn:aws:ssm:...
    ```

    You can run the following command:

    ```shell
    aws-annoying load-variables --env-prefix LOAD_AWS_CONFIG__ -- ...
    ```

    The variables are loaded in the order of option provided, overwriting the variables with the same name in the order of the ARNs.
    Existing environment variables are preserved by default, unless `--overwrite-env` is provided.
    """  # noqa: E501
    command = ctx.args
    if not command:
        logger.warning("No command provided. Exiting...")
        raise typer.Exit(0)

    # Mapping of the ARNs by index (index used for ordering)
    map_arns_by_index = {str(idx): arn for idx, arn in enumerate(arns)}
    if env_prefix:
        logger.info("Loading ARNs from environment variables with prefix: %r", env_prefix)
        arns_env = {
            key.removeprefix(env_prefix): value for key, value in os.environ.items() if key.startswith(env_prefix)
        }
        logger.info("Found %d sources from environment variables.", len(arns_env))
        map_arns_by_index = arns_env | map_arns_by_index

    # Briefly show the ARNs
    table = Table("Index", "ARN")
    for idx, arn in sorted(map_arns_by_index.items()):
        table.add_row(idx, arn)

    # Workaround: The logger cannot directly handle the rich table output.
    with StringIO() as file:
        Console(file=file, emoji=False).print(table)
        table_str = file.getvalue().rstrip()
        logger.info("Summary:\n%s", table_str)

    # Retrieve the variables
    loader = VariableLoader()
    logger.info("Retrieving variables from AWS resources...")
    try:
        variables, load_stats = loader.load(map_arns_by_index)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load the variables: %s", exc)  # noqa: TRY400
        raise typer.Exit(1) from None

    logger.info("Retrieved %d secrets and %d parameters.", load_stats["secrets"], load_stats["parameters"])

    # Prepare the environment variables
    env = os.environ.copy()
    if overwrite_env:
        env.update(variables)
    else:
        # Update variables, preserving the existing ones
        for key, value in variables.items():
            env.setdefault(key, str(value))

    # Run the command with the variables injected as environment variables, replacing current process
    logger.info("Running the command: [bold orchid]%s[/bold orchid]", " ".join(command))
    if replace:  # pragma: no cover (not coverable)
        os.execvpe(command[0], command, env=env)  # noqa: S606
        # The above line should never return

    result = subprocess.run(command, env=env, check=False)  # noqa: S603
    raise typer.Exit(result.returncode)

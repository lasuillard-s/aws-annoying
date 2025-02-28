# flake8: noqa: B008
from __future__ import annotations

import json
import os
import subprocess
from typing import Any, NoReturn, Optional

import boto3
import typer
from rich.console import Console
from rich.table import Table

from .app import app


@app.command(
    context_settings={
        # Allow extra arguments for user provided command
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
)
def load_variables(  # noqa: PLR0913
    *,
    ctx: typer.Context,
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
    quiet: bool = typer.Option(
        False,  # noqa: FBT003
        help="Suppress all outputs from this command.",
    ),
    dry_run: bool = typer.Option(
        False,  # noqa: FBT003
        help="Print the progress only. Neither load variables nor run the command.",
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
    console = Console(quiet=quiet, emoji=False)

    command = ctx.args
    if not command:
        console.print("⚠️ No command provided. Exiting...")
        raise typer.Exit(0)

    # Mapping of the ARNs by index (index used for ordering)
    map_arns_by_index = {str(idx): arn for idx, arn in enumerate(arns)}
    if env_prefix:
        console.print(f"🔍 Loading ARNs from environment variables with prefix: {env_prefix!r}")
        arns_env = {
            key.removeprefix(env_prefix): value for key, value in os.environ.items() if key.startswith(env_prefix)
        }
        console.print(f"🔍 Found {len(arns_env)} sources from environment variables.")
        map_arns_by_index = arns_env | map_arns_by_index

    # Briefly show the ARNs
    table = Table("Index", "ARN")
    for idx, arn in sorted(map_arns_by_index.items()):
        table.add_row(idx, arn)

    console.print(table)

    # Retrieve the variables
    variables = _load_variables(map_arns_by_index, console=console, dry_run=dry_run)

    # Prepare the environment variables
    env = os.environ.copy()
    if overwrite_env:
        env.update(variables)
    else:
        # Update variables, preserving the existing ones
        for key, value in variables.items():
            env.setdefault(key, str(value))

    # Run the command with the variables injected as environment variables, replacing current process
    console.print(f"🚀 Running the command: [bold orchid]{' '.join(command)}[/bold orchid]")
    if replace:  # pragma: no cover (not coverable)
        os.execvpe(command[0], command, env=env)  # noqa: S606
        # The above line should never return

    result = subprocess.run(command, env=env, check=False)  # noqa: S603
    raise typer.Exit(result.returncode)


# TODO(lasuillard): Currently not using pagination (do we need more than 10-20 secrets or parameters each?)
#                   ; consider adding it if needed
def _load_variables(map_arns: dict[str, _ARN], *, console: Console, dry_run: bool) -> dict[str, Any]:
    """Load the variables from the AWS Secrets Manager and SSM Parameter Store.

    Each secret or parameter should be a valid dictionary, where the keys are the variable names
    and the values are the variable values.

    The items are merged in the order of the key of provided mapping, overwriting the variables with the same name
    in the order of the keys.
    """
    console.print("🔍 Retrieving variables from AWS resources...")
    if dry_run:
        console.print("⚠️ Dry run mode enabled. Variables won't be loaded from AWS.")

    # Split the ARNs by resource types
    secrets_map, parameters_map = {}, {}
    for idx, arn in map_arns.items():
        if arn.startswith("arn:aws:secretsmanager:"):
            secrets_map[idx] = arn
        elif arn.startswith("arn:aws:ssm:"):
            parameters_map[idx] = arn
        else:
            msg = f"ARN of unsupported resource: {arn!r}"
            raise ValueError(msg)

    if secrets_map.keys() & parameters_map.keys():
        msg = "Keys in secrets and parameters MUST NOT conflict."
        raise ValueError(msg)

    # Retrieve variables from AWS resources
    secrets: dict[str, _Variables]
    parameters: dict[str, _Variables]
    if dry_run:
        secrets = {idx: {} for idx, _ in secrets_map.items()}
        parameters = {idx: {} for idx, _ in parameters_map.items()}
    else:
        secrets = _retrieve_secrets(secrets_map)
        parameters = _retrieve_parameters(parameters_map)

    console.print(f"✅ Retrieved {len(secrets)} secrets and {len(parameters)} parameters.")

    # Merge the variables in order
    full_variables = secrets | parameters  # Keys MUST NOT conflict
    merged_in_order = {}
    for _, variables in sorted(full_variables.items()):
        merged_in_order.update(variables)

    return merged_in_order


# Type aliases for readability
_ARN = str
_Variables = dict[str, Any]


def _retrieve_secrets(secrets_map: dict[str, _ARN]) -> dict[str, _Variables]:
    """Retrieve the secrets from AWS Secrets Manager."""
    if not secrets_map:
        return {}

    secretsmanager = boto3.client("secretsmanager")

    # Retrieve the secrets
    arns = list(secrets_map.values())
    response = secretsmanager.batch_get_secret_value(SecretIdList=arns)
    if errors := response["Errors"]:
        msg = f"Failed to retrieve secrets: {errors!r}"
        raise ValueError(msg)

    # Parse the secrets
    secrets = response["SecretValues"]
    result = {}
    for secret in secrets:
        arn = secret["ARN"]
        order_key = next(key for key, value in secrets_map.items() if value == arn)
        data = json.loads(secret["SecretString"])
        if not isinstance(data, dict):
            msg = f"Secret data must be a valid dictionary, but got: {type(data)!r}"
            raise TypeError(msg)

        result[order_key] = data

    return result


def _retrieve_parameters(parameters_map: dict[str, _ARN]) -> dict[str, _Variables]:
    """Retrieve the parameters from AWS SSM Parameter Store."""
    if not parameters_map:
        return {}

    ssm = boto3.client("ssm")

    # Retrieve the parameters
    parameter_names = list(parameters_map.values())
    response = ssm.get_parameters(Names=parameter_names, WithDecryption=True)
    if errors := response["InvalidParameters"]:
        msg = f"Failed to retrieve parameters: {errors!r}"
        raise ValueError(msg)

    # Parse the parameters
    parameters = response["Parameters"]
    result = {}
    for parameter in parameters:
        arn = parameter["ARN"]
        order_key = next(key for key, value in parameters_map.items() if value == arn)
        data = json.loads(parameter["Value"])
        if not isinstance(data, dict):
            msg = f"Parameter data must be a valid dictionary, but got: {type(data)!r}"
            raise TypeError(msg)

        result[order_key] = data

    return result

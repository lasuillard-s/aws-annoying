# flake8: noqa: B008
from __future__ import annotations

import json
import os
from typing import Any, NoReturn

import boto3
import typer

from .app import app


@app.command(
    context_settings={
        # Allow extra arguments for user provided command
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
)
def load_variables(
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
    overwrite_env: bool = typer.Option(
        False,  # noqa: FBT003
        help="Overwrite the existing environment variables with the same name.",
    ),
) -> NoReturn:
    """Wrapper command to run command with AWS secrets & parameters injected as environment variables.

    This script is intended to be used in the ECS environment, where currently AWS does not support
    injecting whole JSON dictionary of secrets or parameters as environment variables directly.

    It first loads the variables from the AWS sources then runs the command with the variables injected as environment variables.

    The variable takes precedence as follows:

    - The variables are loaded in the order of the ARNs, overwriting the variables with the same name in the order of the ARNs.
    - The existing environment variables are preserved by default, unless `--overwrite-env` is provided.
    """  # noqa: E501
    command = ctx.args
    if not command:
        raise typer.Exit(0)

    # Mapping of the ARNs by index (index used for ordering)
    # TODO(lasuillard): Allow users to define custom priority keys (options passed via environment variables)
    #                   e.g. `AWS_LOAD_VARIABLES__001_app_config=arn:aws:secretsmanager:...`
    map_arns_by_index = {str(idx): arn for idx, arn in enumerate(arns)}

    # Retrieve the variables
    variables = _load_variables(map_arns=map_arns_by_index)

    # Prepare the environment variables
    env = os.environ.copy()
    if overwrite_env:
        env.update(variables)
    else:
        # Update variables, preserving the existing ones
        for key, value in variables.items():
            env.setdefault(key, str(value))

    # Run the command with the variables injected as environment variables, replacing current process
    os.execvpe(command[0], command, env=env)  # noqa: S606


def _load_variables(map_arns: dict[str, _ARN]) -> dict[str, Any]:
    """Load the variables from the AWS Secrets Manager and SSM Parameter Store.

    Each secret or parameter should be a valid dictionary, where the keys are the variable names
    and the values are the variable values.

    The items are merged in the order of the key of provided mapping, overwriting the variables with the same name
    in the order of the keys.
    """
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

    # Retrieve the secrets and parameters
    secrets = _retrieve_secrets(secrets_map)
    parameters = _retrieve_parameters(parameters_map)
    if secrets.keys() & parameters.keys():
        msg = "Keys in secrets and parameters MUST NOT conflict."
        raise ValueError(msg)

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

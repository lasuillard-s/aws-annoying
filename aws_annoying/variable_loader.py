# flake8: noqa: B008
from __future__ import annotations

import json
import logging
from typing import Any, TypedDict

import boto3

logger = logging.getLogger(__name__)

# Type aliases for readability
_ARN = str
_Variables = dict[str, Any]


class _LoadStatsDict(TypedDict):
    secrets: int
    parameters: int


class VariableLoader:  # noqa: D101
    def __init__(self, *, session: boto3.session.Session | None = None) -> None:
        """Initialize variable loader.

        Args:
            session: Boto3 session to use for AWS operations.
        """
        self.session = session or boto3.session.Session()

    # TODO(lasuillard): Currently not using pagination (do we need more than 10-20 secrets or parameters each?)
    #                   ; consider adding it if needed
    def load(self, map_arns: dict[str, _ARN]) -> tuple[dict[str, Any], _LoadStatsDict]:
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
                msg = f"Unsupported resource: {arn!r}"
                raise ValueError(msg)

        # Retrieve variables from AWS resources
        secrets: dict[str, _Variables]
        parameters: dict[str, _Variables]
        secrets = self._retrieve_secrets(secrets_map)
        parameters = self._retrieve_parameters(parameters_map)

        load_stats: _LoadStatsDict = {
            "secrets": len(secrets),
            "parameters": len(parameters),
        }

        # Merge the variables in order
        full_variables = secrets | parameters  # Keys MUST NOT conflict
        merged_in_order = {}
        for _, variables in sorted(full_variables.items()):
            merged_in_order.update(variables)

        return merged_in_order, load_stats

    def _retrieve_secrets(self, secrets_map: dict[str, _ARN]) -> dict[str, _Variables]:
        """Retrieve the secrets from AWS Secrets Manager."""
        if not secrets_map:
            return {}

        secretsmanager = self.session.client("secretsmanager")

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

    def _retrieve_parameters(self, parameters_map: dict[str, _ARN]) -> dict[str, _Variables]:
        """Retrieve the parameters from AWS SSM Parameter Store."""
        if not parameters_map:
            return {}

        ssm = self.session.client("ssm")

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

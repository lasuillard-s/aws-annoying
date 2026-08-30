import json
from typing import Any

import boto3

# Type aliases for better readability
Name = str
Value = Any
ARN = str


def create_secrets(kv: dict[Name, Value]) -> dict[Name, ARN]:
    secretsmanager = boto3.client("secretsmanager")
    secrets = {}
    for name, value in kv.items():
        secret = secretsmanager.create_secret(
            Name=name,
            SecretString=json.dumps(value),
        )
        secrets[name] = secret["ARN"]

    return secrets


def create_parameters(kv: dict[Name, Value]) -> dict[Name, ARN]:
    ssm = boto3.client("ssm")
    parameters = {}
    for name, value in kv.items():
        ssm.put_parameter(
            Name=name,
            Value=json.dumps(value),
            Type="String",
        )
        parameter = ssm.get_parameter(Name=name)["Parameter"]
        parameters[name] = parameter["ARN"]

    return parameters

import json
import os
import subprocess
from itertools import chain
from pathlib import Path

import boto3
from typer.testing import CliRunner

from aws_annoying.main import app

# * Command `load-variables` cannot use Typer CLI runner because it uses `os.execvpe` internally,
# * which replaces the current process with the new one, breaking pytest runtime.
# * But tests that does not reach the `os.execvpe` statement can use Typer CLI runner.
runner = CliRunner()


def test_nothing() -> None:
    """If nothing is provided, the command should do nothing."""
    # Arrange
    # ...

    # Act
    result = runner.invoke(
        app,
        [
            "load-variables",
        ],
    )

    # Assert
    assert result.exit_code == 0
    assert result.stdout == "⚠️  No command provided. Exiting...\n"


def test_load_variables(moto_server: str) -> None:
    """If nothing is provided, the command should do nothing."""
    # Arrange
    secretsmanager = boto3.client("secretsmanager")
    django_sensitive_settings = secretsmanager.create_secret(
        Name="my-app/django-sensitive-settings",
        SecretString=json.dumps({"DJANGO_SECRET_KEY": "my-secret-key"}),
    )

    ssm = boto3.client("ssm")
    ssm.put_parameter(
        Name="/my-app/django-settings",
        Value=json.dumps(
            {
                "DJANGO_SETTINGS_MODULE": "config.settings.local",
                "DJANGO_ALLOWED_HOSTS": "*",
                "DJANGO_DEBUG": "False",
            },
        ),
        Type="String",
    )
    django_settings = ssm.get_parameter(Name="/my-app/django-settings")
    ssm.put_parameter(
        Name="/my-app/override",
        Value=json.dumps(
            {
                "DJANGO_ALLOWED_HOSTS": "127.0.0.1,192.168.0.2",
            },
        ),
        Type="SecureString",
    )
    override = ssm.get_parameter(Name="/my-app/override")

    # Act
    arns_to_load = [
        django_sensitive_settings["ARN"],
        django_settings["Parameter"]["ARN"],
    ]
    args = [
        "load-variables",
        *chain.from_iterable(("--arns", arn) for arn in arns_to_load),
        "--env-prefix",
        "LOAD_AWS_CONFIG__",
        "--",
        str((Path(__file__).parent / "_helpers" / "printenv.py").absolute()),
        "DJANGO_SETTINGS_MODULE",
        "DJANGO_SECRET_KEY",
        "DJANGO_DEBUG",
        "DJANGO_ALLOWED_HOSTS",
    ]
    env = (
        os.environ
        | {
            # Direct environment variables
            "LOAD_AWS_CONFIG__900_override": override["Parameter"]["ARN"],
            "DJANGO_SETTINGS_MODULE": "config.settings.development",
        }
        | {
            # Test environment variables
            "AWS_ENDPOINT_URL": moto_server,
        }
    )
    result = subprocess.run(  # noqa: S603
        ["uv", "run", "aws-annoying", *args],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    # Assert
    assert result.returncode == 0
    assert (
        result.stdout.strip()
        == """
🔍 Loading ARNs from environment variables with prefix: 'LOAD_AWS_CONFIG__'
🔍 Found 1 sources from environment variables.
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Index        ┃ ARN                                                           ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 0            │ arn:aws:secretsmanager:us-east-1:123456789012:secret:my-app/… │
│ 1            │ arn:aws:ssm:us-east-1:123456789012:parameter/my-app/django-s… │
│ 900_override │ arn:aws:ssm:us-east-1:123456789012:parameter/my-app/override  │
└──────────────┴───────────────────────────────────────────────────────────────┘
🔍 Retrieving variables from AWS resources...
✅ Retrieved 1 secrets and 2 parameters.
🚀 Running the command with the variables injected as environment variables...
DJANGO_SETTINGS_MODULE=config.settings.development
DJANGO_SECRET_KEY=my-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,192.168.0.2
""".strip()
    )
    assert result.stderr == ""

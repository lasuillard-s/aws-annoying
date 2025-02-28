import json
import os
import subprocess
from pathlib import Path

import boto3
import pytest
from typer.testing import CliRunner

from aws_annoying.main import app

from ._helpers import normalize_console_output, repeat_options

# * Command `load-variables` cannot use Typer CLI runner because it uses `os.execvpe` internally,
# * which replaces the current process with the new one, breaking pytest runtime.
# * But tests that does not reach the `os.execvpe` statement can use Typer CLI runner.
runner = CliRunner()

_VariablesFixture = dict[str, dict[str, str]]


@pytest.fixture
def setup_variables() -> _VariablesFixture:
    # Secrets
    secretsmanager = boto3.client("secretsmanager")
    django_sensitive_settings = secretsmanager.create_secret(
        Name="my-app/django-sensitive-settings",
        SecretString=json.dumps({"DJANGO_SECRET_KEY": "my-secret-key"}),
    )

    # Parameters
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

    return {
        "secrets": {
            "django-sensitive-settings": django_sensitive_settings["ARN"],
        },
        "parameters": {
            "django-settings": django_settings["Parameter"]["ARN"],
            "override": override["Parameter"]["ARN"],
        },
    }


printenv_py = str(Path(__file__).parent / "_helpers" / "scripts" / "printenv.py")


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


def test_load_variables_replace(moto_server: str, setup_variables: _VariablesFixture) -> None:
    """If nothing is provided, the command should do nothing."""
    # Arrange
    arns_to_load = [
        setup_variables["secrets"]["django-sensitive-settings"],
        setup_variables["parameters"]["django-settings"],
    ]
    args = [
        "load-variables",
        *repeat_options("--arns", arns_to_load),
        "--env-prefix",
        "LOAD_AWS_CONFIG__",
        "--",
        printenv_py,
        "DJANGO_SETTINGS_MODULE",
        "DJANGO_SECRET_KEY",
        "DJANGO_DEBUG",
        "DJANGO_ALLOWED_HOSTS",
    ]
    env = (
        os.environ
        | {
            # Direct environment variables
            "LOAD_AWS_CONFIG__900_override": setup_variables["parameters"]["override"],
            "DJANGO_SETTINGS_MODULE": "config.settings.development",
        }
        | {
            # Test environment variables for subprocess
            "AWS_ENDPOINT_URL": moto_server,
        }
    )

    # Act
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
        normalize_console_output(result.stdout)
        == f"""
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
🚀 Running the command:
{printenv_py}
DJANGO_SETTINGS_MODULE DJANGO_SECRET_KEY DJANGO_DEBUG DJANGO_ALLOWED_HOSTS
DJANGO_SETTINGS_MODULE=config.settings.development
DJANGO_SECRET_KEY=my-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,192.168.0.2
""".strip()
    )
    assert result.stderr == ""


def test_load_variables_no_replace(moto_server: str, setup_variables: _VariablesFixture) -> None:
    """If nothing is provided, the command should do nothing."""
    # Arrange
    arns_to_load = [
        setup_variables["secrets"]["django-sensitive-settings"],
        setup_variables["parameters"]["django-settings"],
    ]
    args = [
        "load-variables",
        *repeat_options("--arns", arns_to_load),
        "--env-prefix",
        "LOAD_AWS_CONFIG__",
        "--no-replace",
        "--",
        printenv_py,
        "DJANGO_SETTINGS_MODULE",
        "DJANGO_SECRET_KEY",
        "DJANGO_DEBUG",
        "DJANGO_ALLOWED_HOSTS",
    ]
    env = (
        os.environ
        | {
            # Direct environment variables
            "LOAD_AWS_CONFIG__900_override": setup_variables["parameters"]["override"],
            "DJANGO_SETTINGS_MODULE": "config.settings.development",
        }
        | {
            # Test environment variables for subprocess
            "AWS_ENDPOINT_URL": moto_server,
        }
    )

    # Act
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
        normalize_console_output(result.stdout)
        == f"""
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
🚀 Running the command:
{printenv_py}
DJANGO_SETTINGS_MODULE DJANGO_SECRET_KEY DJANGO_DEBUG DJANGO_ALLOWED_HOSTS
DJANGO_SETTINGS_MODULE=config.settings.development
DJANGO_SECRET_KEY=my-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,192.168.0.2
""".strip()
    )
    assert result.stderr == ""

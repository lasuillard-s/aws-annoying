from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from typer.testing import CliRunner

from aws_annoying.cli.main import app
from tests.cli._helpers import create_parameters, create_secrets

from ._helpers import PRINTENV_PY, invoke_cli, normalize_console_output, repeat_options

if TYPE_CHECKING:
    from pytest_snapshot.plugin import Snapshot

# * Command `load-variables` cannot use Typer CLI runner because it uses `os.execvpe` internally,
# * which replaces the current process with the new one, breaking pytest runtime.
# * But tests that does not reach the `os.execvpe` statement can use Typer CLI runner (or provide `--no-replace` flag).
runner = CliRunner()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("use_localstack"),
    pytest.mark.docker,
]


@pytest.fixture
def set_terminal_width() -> int:
    """Use small terminal to simplify test assertions (due to secret random suffix)."""
    return 80


def setup_resources(*, env_base: dict[str, str] | None = None) -> dict[str, Any]:
    """Set up AWS resources for tests."""
    # Secrets
    secrets = create_secrets(
        {
            # Pass to CLI arguments
            "my-app/django-sensitive-settings": {
                "DJANGO_SECRET_KEY": "my-secret-key",
            },
        },
    )

    # Parameters
    parameters = create_parameters(
        {
            # Pass to CLI arguments
            "/my-app/django-settings": {
                "DJANGO_SETTINGS_MODULE": "config.settings.local",
                "DJANGO_ALLOWED_HOSTS": "*",
                "DJANGO_DEBUG": "False",
            },
            # Pass to execution environment
            "/my-app/override": {
                "DJANGO_ALLOWED_HOSTS": "127.0.0.1,192.168.0.2",
            },
        },
    )

    # Load as environment variables
    env = env_base or os.environ | {
        # Direct environment variables
        "LOAD_AWS_CONFIG__900_override": parameters["/my-app/override"],
        "DJANGO_SETTINGS_MODULE": "config.settings.development",
    }

    # Load resources by passing as CLI arguments
    load_resources = [
        secrets["my-app/django-sensitive-settings"],
        parameters["/my-app/django-settings"],
    ]

    return {
        # Test environment
        "env": env,
        "load_resources": load_resources,
        # Resources
        "secrets": secrets,
        "parameters": parameters,
    }


printenv_py = str(PRINTENV_PY.relative_to(Path.cwd()))
printenv = [printenv_py, "DJANGO_SETTINGS_MODULE", "DJANGO_SECRET_KEY", "DJANGO_DEBUG", "DJANGO_ALLOWED_HOSTS"]


def test_nothing(snapshot: Snapshot) -> None:
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
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")


def test_basic(snapshot: Snapshot) -> None:
    """Test basic usage."""
    # Arrange
    setup = setup_resources()

    # Act
    result = invoke_cli(
        "load-variables",
        *repeat_options("--arns", setup["load_resources"]),
        "--no-replace",
        "--",
        *printenv,
        env=setup["env"],
    )

    # Assert
    assert result.returncode == 0
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""


def test_replace_quiet(snapshot: Snapshot) -> None:
    """Test the most common practical use-case."""
    # Arrange
    setup = setup_resources()

    # Act
    result = invoke_cli(
        "--quiet",
        "load-variables",
        *repeat_options("--arns", setup["load_resources"]),
        "--env-prefix",
        "LOAD_AWS_CONFIG__",
        "--",
        *printenv,
        env=setup["env"],
    )

    # Assert
    assert result.returncode == 0
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""


def test_env_prefix(snapshot: Snapshot) -> None:
    """Test prefixed environment variables support."""
    # Arrange
    setup = setup_resources()

    # Act
    result = invoke_cli(
        "load-variables",
        *repeat_options("--arns", setup["load_resources"]),
        "--env-prefix",
        "LOAD_AWS_CONFIG__",
        "--no-replace",
        "--",
        *printenv,
        env=setup["env"],
    )

    # Assert
    assert result.returncode == 0
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""


def test_overwrite_env(snapshot: Snapshot) -> None:
    """Test `--overwrite-env` flag. If provided, it should overwrite the existing environment variables."""
    # Arrange
    setup = setup_resources()

    # Act
    result = invoke_cli(
        "load-variables",
        *repeat_options("--arns", setup["load_resources"]),
        "--env-prefix",
        "LOAD_AWS_CONFIG__",
        "--no-replace",
        "--overwrite-env",
        "--",
        *printenv,
        env=setup["env"],
    )

    # Assert
    assert result.returncode == 0
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""


def test_unsupported_resource(snapshot: Snapshot) -> None:
    """If unsupported resource ARN provided, should exit with error."""
    # Arrange
    # ...

    # Act
    result = runner.invoke(
        app,
        [
            "load-variables",
            "--arns",
            "arn:aws:s3:::my-bucket/my-object",
            printenv_py,
        ],
    )

    # Assert
    assert result.exit_code == 1
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")


@pytest.mark.parametrize(
    argnames="arn",
    argvalues=[
        # TODO(lasuillard): `batch_get_secret_value` does not raise an error if secret does not exist.
        #                   Consider implementing new flag for strict mode (e.g. `--if-not-exists={error,ignore}`)
        # "arn:aws:secretsmanager:us-east-1:123456789012:secret:unknown-secret", # noqa: ERA001
        "arn:aws:ssm:us-east-1:123456789012:parameter/unknown-parameter",
    ],
    ids=[
        # "secretsmanager",
        "ssm",
    ],
)
def test_resource_not_found(snapshot: Snapshot, arn: str) -> None:
    """Test with resource does not exists."""
    # Arrange
    setup = setup_resources()

    # Act
    result = invoke_cli(
        "load-variables",
        *repeat_options("--arns", setup["load_resources"]),
        "--arns",
        arn,
        "--no-replace",
        "--",
        *printenv,
        env=setup["env"],
    )

    # Assert
    assert result.returncode == 1
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""

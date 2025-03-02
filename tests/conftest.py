from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING, Protocol

import pytest
from moto import mock_aws
from moto.server import ThreadedMotoServer
from typer.testing import CliRunner

if TYPE_CHECKING:
    from collections.abc import Iterator

runner = CliRunner()


@pytest.fixture
def aws_credentials() -> Iterator[None]:
    """Mock AWS Credentials for Moto."""
    old_env = os.environ.copy()
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"  # noqa: S105
    os.environ["AWS_SECURITY_TOKEN"] = "testing"  # noqa: S105
    os.environ["AWS_SESSION_TOKEN"] = "testing"  # noqa: S105
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    yield
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture(autouse=True)
def mocked_aws(aws_credentials: None) -> Iterator[None]:  # noqa: ARG001
    """Mock all AWS interactions."""
    with mock_aws():
        yield


@pytest.fixture(scope="module")
def moto_server() -> Iterator[str]:
    """Run a Moto server for AWS mocking."""
    server = ThreadedMotoServer()
    server.start()
    host, port = server.get_host_and_port()
    yield f"http://{host}:{port}"
    server.stop()


class Invoker(Protocol):
    def __call__(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]: ...


@pytest.fixture(scope="module")
def invoke_cli(moto_server: str) -> Invoker:
    """Returns callable to invoke CLI as subprocess, with Moto server configured."""

    def func(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            ["uv", "run", "aws-annoying", *args],  # noqa: S607
            check=False,
            capture_output=True,
            text=True,
            env=(env or os.environ) | {"AWS_ENDPOINT_URL": moto_server},
        )

    return func

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING, Protocol

import pytest
from moto import mock_aws
from moto.server import ThreadedMotoServer
from testcontainers.localstack import LocalStackContainer
from typer.testing import CliRunner

if TYPE_CHECKING:
    from collections.abc import Iterator

runner = CliRunner()


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock AWS Credentials for Moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    # Intentionally malform `AWS_ENDPOINT_URL` environment variable to prevent running tests from the user environment
    # which highly likely malicious to the user's AWS account.
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://aws-not-configured:wrong-port")


# Moto
# ----------------------------------------------------------------------------
@pytest.fixture
def use_moto(monkeypatch: pytest.MonkeyPatch, aws_credentials: None) -> Iterator[None]:  # noqa: ARG001
    """Mock all AWS interactions."""
    # Also, Moto does not work well with existing LocalStack; so unset `AWS_ENDPOINT_URL`
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    with mock_aws():
        yield


# Moto Server
# ----------------------------------------------------------------------------
@pytest.fixture(scope="module")
def moto_server() -> Iterator[str]:
    """Run a Moto server for AWS mocking."""
    server = ThreadedMotoServer()
    server.start()
    host, port = server.get_host_and_port()
    yield f"http://{host}:{port}"
    server.stop()


@pytest.fixture
def use_moto_server(monkeypatch: pytest.MonkeyPatch, moto_server: str) -> None:
    """Use Moto server for AWS mocking."""
    monkeypatch.setenv("AWS_ENDPOINT_URL", moto_server)


# LocalStack
# ----------------------------------------------------------------------------
@pytest.fixture
def localstack(request: pytest.FixtureRequest) -> str:
    """Run Localstack for AWS mocking."""
    container = LocalStackContainer(image="localstack/localstack:4")
    container.start()

    def teardown() -> None:
        container.stop()

    request.addfinalizer(teardown)  # noqa: PT021
    return container.get_url()  # type: ignore[no-any-return]


@pytest.fixture
def use_localstack(monkeypatch: pytest.MonkeyPatch, localstack: str) -> None:
    """Use Localstack for AWS mocking."""
    monkeypatch.setenv("AWS_ENDPOINT_URL", localstack)


# CLI helper
# ----------------------------------------------------------------------------
class Invoker(Protocol):
    def __call__(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]: ...


@pytest.fixture(scope="module")
def invoke_cli() -> Invoker:
    """Returns callable to invoke CLI as subprocess."""

    def func(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            ["uv", "run", "aws-annoying", *args],  # noqa: S607
            check=False,
            capture_output=True,
            text=True,
            env=(env or os.environ),  # * `AWS_ENDPOINT_URL` should be inherited appropriately to use Moto or LocalStack
        )

    return func

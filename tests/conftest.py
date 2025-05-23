from __future__ import annotations

from configparser import ConfigParser
from typing import TYPE_CHECKING

import pytest
from moto import mock_aws
from moto.server import ThreadedMotoServer
from testcontainers.localstack import LocalStackContainer
from typer.testing import CliRunner

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

runner = CliRunner()


@pytest.fixture
def set_terminal_width() -> int:
    """Set console width."""
    return 200


@pytest.fixture(autouse=True)
def patch_terminal_width(monkeypatch: pytest.MonkeyPatch, set_terminal_width: int) -> None:
    """Patch the console width."""
    monkeypatch.setenv("COLUMNS", str(set_terminal_width))


# AWS
# ----------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Mock AWS Credentials."""
    aws_credentials = tmp_path / "credentials"
    ini = ConfigParser()
    ini["default"] = {
        "aws_access_key_id": "testing",
        "aws_secret_access_key": "testing",
        "aws_session_token": "testing",
        "aws_security_token": "testing",
        "region": "us-east-1",
    }
    with aws_credentials.open("w") as f:
        ini.write(f)

    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(aws_credentials))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "config"))

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
# https://testcontainers.com/guides/getting-started-with-testcontainers-for-python/
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

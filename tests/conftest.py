import os
from collections.abc import Iterator

import pytest
from moto import mock_aws
from moto.server import ThreadedMotoServer
from typer.testing import CliRunner

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

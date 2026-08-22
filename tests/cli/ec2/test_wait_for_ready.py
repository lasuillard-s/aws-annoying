from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

import boto3
import pytest

from tests.cli._helpers import normalize_console_output

if TYPE_CHECKING:
    from pytest_snapshot.plugin import Snapshot
from botocore.stub import Stubber
from typer.testing import CliRunner

from aws_annoying.cli.main import app
from aws_annoying.ec2 import (
    InstanceNotFoundError,
    InstanceNotReadyError,
    make_ssm_checker,
)

runner = CliRunner()

pytestmark = [
    pytest.mark.unit,
]


def test_invalid_instance_id(snapshot: Snapshot) -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "invalid-instance-name",
        ],
    )

    # Assert
    assert result.exit_code == 1
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""


def test_invalid_document_parameters_json(snapshot: Snapshot) -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--document-parameters",
            "not-valid-json",
        ],
    )

    # Assert
    assert result.exit_code == 2
    assert result.stdout == ""
    snapshot.assert_match(normalize_console_output(result.stderr), "stderr.txt")


def test_invalid_document_parameters_not_dict(snapshot: Snapshot) -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--document-parameters",
            '["not", "a", "dict"]',
        ],
    )

    # Assert
    assert result.exit_code == 2
    assert result.stdout == ""
    snapshot.assert_match(normalize_console_output(result.stderr), "stderr.txt")


@mock.patch("aws_annoying.cli.ec2.wait_for_ready.detect_instance_platform")
def test_dry_run_success(mock_detect: mock.MagicMock, snapshot: Snapshot) -> None:
    # Arrange
    mock_detect.return_value = "linux"

    # Act
    result = runner.invoke(
        app,
        [
            "--dry-run",
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
        ],
    )

    # Assert
    assert result.exit_code == 0
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""


def test_dry_run_windows(snapshot: Snapshot) -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "--dry-run",
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--platform",
            "windows",
        ],
    )

    # Assert
    assert result.exit_code == 0
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""


def test_dry_run_invalid_id(snapshot: Snapshot) -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "--dry-run",
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "my-web-server",
        ],
    )

    # Assert
    assert result.exit_code == 1
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""


@mock.patch("aws_annoying.cli.ec2.wait_for_ready.wait_for_instance_ready")
@mock.patch("aws_annoying.cli.ec2.wait_for_ready.detect_instance_platform")
def test_wait_for_ready_success_auto(
    mock_detect: mock.MagicMock,
    mock_wait: mock.MagicMock,
    snapshot: Snapshot,
) -> None:
    # Arrange
    mock_detect.return_value = "linux"
    mock_wait.return_value = True

    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--max-attempts",
            "5",
            "--delay",
            "10",
        ],
    )

    # Assert
    assert result.exit_code == 0
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""
    mock_detect.assert_called_once_with("i-0123456789abcdef0")
    mock_wait.assert_called_once_with(
        instance_id="i-0123456789abcdef0",
        checker=mock.ANY,  # The actual checker function is not important for this test
        max_attempts=5,
        delay=10.0,
    )


@mock.patch("aws_annoying.cli.ec2.wait_for_ready.wait_for_instance_ready")
def test_wait_for_ready_success_windows(mock_wait: mock.MagicMock, snapshot: Snapshot) -> None:
    # Arrange
    mock_wait.return_value = True

    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--platform",
            "windows",
        ],
    )

    # Assert
    assert result.exit_code == 0
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""
    mock_wait.assert_called_once_with(
        instance_id="i-0123456789abcdef0",
        checker=mock.ANY,  # The actual checker function is not important for this test
        max_attempts=10,
        delay=30.0,
    )


@mock.patch("aws_annoying.cli.ec2.wait_for_ready.wait_for_instance_ready")
def test_wait_for_ready_custom_document_with_parameters(mock_wait: mock.MagicMock, snapshot: Snapshot) -> None:
    # Arrange
    mock_wait.return_value = True

    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--document-name",
            "MyCustomDoc",
            "--document-parameters",
            '{"commands": ["exit 0"]}',
        ],
    )

    # Assert
    assert result.exit_code == 0
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""
    assert mock_wait.call_count == 1
    call_kwargs = mock_wait.call_args.kwargs
    assert call_kwargs["checker"] is not None


@mock.patch("aws_annoying.cli.ec2.wait_for_ready.detect_instance_platform")
def test_wait_for_ready_not_found_failure(
    mock_detect: mock.MagicMock,
) -> None:
    # Arrange
    mock_detect.side_effect = InstanceNotFoundError("Instance not found")

    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
        ],
    )

    # Assert
    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr == ""


@mock.patch("aws_annoying.cli.ec2.wait_for_ready.wait_for_instance_ready")
def test_wait_for_ready_not_ready_failure(mock_wait: mock.MagicMock, snapshot: Snapshot) -> None:
    # Arrange
    mock_wait.side_effect = InstanceNotReadyError("Failed after max attempts")

    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--platform",
            "linux",
        ],
    )

    # Assert
    assert result.exit_code == 1
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""


def test_build_custom_ssm_checker_default_params_success() -> None:
    # Arrange
    checker = make_ssm_checker("MyCustomDoc", {"commands": ["echo 'ready'"]})
    session = mock.MagicMock()
    ssm = boto3.client("ssm", region_name="us-east-1")
    session.client.return_value = ssm

    stubber = Stubber(ssm)
    stubber.add_response(
        "send_command",
        {"Command": {"CommandId": "00000000-0000-0000-0000-000000000001"}},
        expected_params={
            "InstanceIds": ["i-0123456789abcdef0"],
            "DocumentName": "MyCustomDoc",
            "Parameters": {"commands": ["echo 'ready'"]},
        },
    )
    stubber.add_response(
        "get_command_invocation",
        {
            "Status": "Success",
            "ResponseCode": 0,
        },
        expected_params={
            "CommandId": "00000000-0000-0000-0000-000000000001",
            "InstanceId": "i-0123456789abcdef0",
        },
    )

    # Act & Assert
    with mock.patch("time.sleep"), stubber:
        assert checker("i-0123456789abcdef0", session=session) is True


def test_build_custom_ssm_checker_custom_params_failure() -> None:
    # Arrange
    checker = make_ssm_checker("MyCustomDoc", {"commands": ["exit 0"]})
    session = mock.MagicMock()
    ssm = boto3.client("ssm", region_name="us-east-1")
    session.client.return_value = ssm

    stubber = Stubber(ssm)
    stubber.add_client_error(
        "send_command",
        service_error_code="InvalidDocument",
        service_message="Document not found",
        expected_params={
            "InstanceIds": ["i-0123456789abcdef0"],
            "DocumentName": "MyCustomDoc",
            "Parameters": {"commands": ["exit 0"]},
        },
    )

    # Act & Assert
    with stubber:
        assert checker("i-0123456789abcdef0", session=session) is False

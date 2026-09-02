from unittest import mock

import boto3
import botocore.exceptions
import pytest
from botocore.stub import Stubber

from aws_annoying.ec2 import (
    InstanceNotReadyError,
    InstanceReadinessWaiter,
    InvalidInstanceIdError,
)

pytestmark = [
    pytest.mark.unit,
]


class Test_InstanceReadinessWaiter:
    def test_invalid_instance_id(self) -> None:
        """Test waiting with an invalid EC2 instance ID raises InvalidInstanceIdError."""
        # Arrange
        ssm = boto3.client("ssm", region_name="us-east-1")
        waiter = InstanceReadinessWaiter("AWS-RunShellScript", {"commands": ["echo 'ready'"]}, client=ssm)

        # Act & Assert
        with pytest.raises(InvalidInstanceIdError, match=r"Invalid EC2 instance ID: 'not-an-id'"):
            waiter.wait_for_ready("not-an-id")

    def test_wait_for_ready_success(self) -> None:
        """Test waiting succeeds on the first attempt when instance is ready."""
        # Arrange
        ssm = boto3.client("ssm", region_name="us-east-1")
        waiter = InstanceReadinessWaiter("AWS-RunShellScript", {"commands": ["echo 'ready'"]}, client=ssm)

        # Act
        with mock.patch.object(waiter, "check_ready", return_value=True) as mock_check, mock.patch("time.sleep"):
            result = waiter.wait_for_ready("i-0123456789abcdef0", max_attempts=3)

        # Assert
        assert result is True
        mock_check.assert_called_once_with("i-0123456789abcdef0")

    def test_wait_for_ready_multiple_attempts(self) -> None:
        """Test waiting succeeds after multiple retry attempts."""
        # Arrange
        ssm = boto3.client("ssm", region_name="us-east-1")
        waiter = InstanceReadinessWaiter("AWS-RunShellScript", {"commands": ["echo 'ready'"]}, client=ssm)

        # Act
        with (
            mock.patch.object(waiter, "check_ready", side_effect=[False, True]) as mock_check,
            mock.patch("time.sleep") as mock_sleep,
        ):
            result = waiter.wait_for_ready("i-0123456789abcdef0", max_attempts=3, delay=0.1)

        # Assert
        assert result is True
        assert mock_check.call_count == 2
        mock_sleep.assert_called_once_with(0.1)

    def test_wait_for_ready_max_attempts_exceeded(self) -> None:
        """Test waiting raises InstanceNotReadyError when max attempts are exceeded."""
        # Arrange
        ssm = boto3.client("ssm", region_name="us-east-1")
        waiter = InstanceReadinessWaiter("AWS-RunShellScript", {"commands": ["echo 'ready'"]}, client=ssm)

        # Act & Assert
        with (
            mock.patch.object(waiter, "check_ready", return_value=False),
            mock.patch("time.sleep"),
            pytest.raises(InstanceNotReadyError, match=r"failed to become ready after 2 attempts"),
        ):
            waiter.wait_for_ready("i-0123456789abcdef0", max_attempts=2, delay=0.1)

    def test_check_ready_success(self) -> None:
        """Test check_ready returns True when command invocation succeeds."""
        # Arrange
        ssm = boto3.client("ssm", region_name="us-east-1")
        waiter = InstanceReadinessWaiter(
            "MyCustomDoc",
            {"commands": ["echo 'ready'"]},
            client=ssm,
            wait_duration=2.0,
        )

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
        with mock.patch.object(waiter, "wait") as mock_wait, stubber:
            assert waiter.check_ready("i-0123456789abcdef0") is True
            mock_wait.assert_called_once()

    def test_check_ready_transient_failure_send_command(self) -> None:
        """Test check_ready returns False when send_command fails with a transient error."""
        # Arrange
        ssm = boto3.client("ssm", region_name="us-east-1")
        waiter = InstanceReadinessWaiter("MyCustomDoc", {"commands": ["exit 0"]}, client=ssm)

        stubber = Stubber(ssm)
        stubber.add_client_error(
            "send_command",
            service_error_code="InvalidInstanceId",
            service_message="Instance is not in valid state",
            expected_params={
                "InstanceIds": ["i-0123456789abcdef0"],
                "DocumentName": "MyCustomDoc",
                "Parameters": {"commands": ["exit 0"]},
            },
        )

        # Act & Assert
        with stubber:
            assert waiter.check_ready("i-0123456789abcdef0") is False

    def test_check_ready_transient_failure_get_command_invocation(self) -> None:
        """Test check_ready returns False when get_command_invocation fails with InvocationDoesNotExist."""
        # Arrange
        ssm = boto3.client("ssm", region_name="us-east-1")
        waiter = InstanceReadinessWaiter("MyCustomDoc", {"commands": ["exit 0"]}, client=ssm)

        stubber = Stubber(ssm)
        stubber.add_response(
            "send_command",
            {"Command": {"CommandId": "00000000-0000-0000-0000-000000000001"}},
            expected_params={
                "InstanceIds": ["i-0123456789abcdef0"],
                "DocumentName": "MyCustomDoc",
                "Parameters": {"commands": ["exit 0"]},
            },
        )
        stubber.add_client_error(
            "get_command_invocation",
            service_error_code="InvocationDoesNotExist",
            service_message="Invocation does not exist",
            expected_params={
                "CommandId": "00000000-0000-0000-0000-000000000001",
                "InstanceId": "i-0123456789abcdef0",
            },
        )

        # Act & Assert
        with mock.patch.object(waiter, "wait"), stubber:
            assert waiter.check_ready("i-0123456789abcdef0") is False

    def test_check_ready_non_transient_failure_raises(self) -> None:
        """Test check_ready re-raises non-transient ClientErrors."""
        # Arrange
        ssm = boto3.client("ssm", region_name="us-east-1")
        waiter = InstanceReadinessWaiter("MyCustomDoc", {"commands": ["exit 0"]}, client=ssm)

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
        with stubber, pytest.raises(botocore.exceptions.ClientError, match=r"Document not found"):
            waiter.check_ready("i-0123456789abcdef0")

    def test_is_transient_error(self) -> None:
        """Test identifying transient vs non-transient SSM ClientErrors."""
        # Arrange
        ssm = boto3.client("ssm", region_name="us-east-1")
        waiter = InstanceReadinessWaiter("MyCustomDoc", {}, client=ssm)

        transient_err = botocore.exceptions.ClientError(
            {"Error": {"Code": "InvalidInstanceId", "Message": "transient"}},
            "send_command",
        )
        non_transient_err = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "denied"}},
            "send_command",
        )

        # Act & Assert
        assert waiter.is_transient_error(transient_err) is True
        assert waiter.is_transient_error(non_transient_err) is False

    def test_wait(self) -> None:
        """Test wait helper pauses execution for the configured wait_duration."""
        # Arrange
        ssm = boto3.client("ssm", region_name="us-east-1")
        waiter = InstanceReadinessWaiter("MyCustomDoc", {}, client=ssm, wait_duration=3.5)

        # Act
        with mock.patch("time.sleep") as mock_sleep:
            waiter.wait()

        # Assert
        mock_sleep.assert_called_once_with(3.5)

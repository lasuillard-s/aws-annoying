from __future__ import annotations

from unittest import mock

import boto3
import botocore.exceptions
import pytest
from botocore.stub import Stubber

from aws_annoying.ec2 import (
    InstanceNotFoundError,
    InstanceNotReadyError,
    InvalidInstanceIdError,
    detect_instance_platform,
    wait_for_instance_ready,
)

pytestmark = [
    pytest.mark.unit,
]


class Test_detect_instance_platform:
    def test_detect_linux(self) -> None:
        # Arrange
        session = mock.MagicMock()
        ec2 = boto3.client("ec2", region_name="us-east-1")
        session.client.return_value = ec2
        stubber = Stubber(ec2)

        stubber.add_response(
            "describe_instances",
            {
                "Reservations": [
                    {
                        "Instances": [
                            {
                                "InstanceId": "i-0123456789abcdef0",
                                "PlatformDetails": "Linux/UNIX",
                            }
                        ]
                    }
                ]
            },
            expected_params={"InstanceIds": ["i-0123456789abcdef0"]},
        )

        # Act & Assert
        with stubber:
            platform = detect_instance_platform("i-0123456789abcdef0", session=session)
            assert platform == "linux"

    def test_detect_windows_from_platform_field(self) -> None:
        # Arrange
        session = mock.MagicMock()
        ec2 = boto3.client("ec2", region_name="us-east-1")
        session.client.return_value = ec2
        stubber = Stubber(ec2)

        stubber.add_response(
            "describe_instances",
            {
                "Reservations": [
                    {
                        "Instances": [
                            {
                                "InstanceId": "i-0123456789abcdef0",
                                "Platform": "windows",
                                "PlatformDetails": "Windows",
                            }
                        ]
                    }
                ]
            },
            expected_params={"InstanceIds": ["i-0123456789abcdef0"]},
        )

        # Act & Assert
        with stubber:
            platform = detect_instance_platform("i-0123456789abcdef0", session=session)
            assert platform == "windows"

    def test_instance_not_found_empty_reservations(self) -> None:
        # Arrange
        session = mock.MagicMock()
        ec2 = boto3.client("ec2", region_name="us-east-1")
        session.client.return_value = ec2
        stubber = Stubber(ec2)

        stubber.add_response(
            "describe_instances",
            {"Reservations": []},
            expected_params={"InstanceIds": ["i-0123456789abcdef0"]},
        )

        # Act & Assert
        with stubber, pytest.raises(InstanceNotFoundError, match=r"Instance 'i-0123456789abcdef0' not found\."):
            detect_instance_platform("i-0123456789abcdef0", session=session)

    def test_instance_client_error_not_found(self) -> None:
        # Arrange
        session = mock.MagicMock()
        ec2 = boto3.client("ec2", region_name="us-east-1")
        session.client.return_value = ec2
        stubber = Stubber(ec2)

        stubber.add_client_error(
            "describe_instances",
            service_error_code="InvalidInstanceID.NotFound",
            service_message="The instance ID does not exist",
            expected_params={"InstanceIds": ["i-0123456789abcdef0"]},
        )

        # Act & Assert
        with stubber, pytest.raises(InstanceNotFoundError, match=r"Instance 'i-0123456789abcdef0' not found\."):
            detect_instance_platform("i-0123456789abcdef0", session=session)

    def test_instance_client_error_other(self) -> None:
        # Arrange
        session = mock.MagicMock()
        ec2 = boto3.client("ec2", region_name="us-east-1")
        session.client.return_value = ec2
        stubber = Stubber(ec2)

        stubber.add_client_error(
            "describe_instances",
            service_error_code="UnauthorizedOperation",
            service_message="You are not authorized to perform this operation",
            expected_params={"InstanceIds": ["i-0123456789abcdef0"]},
        )

        # Act & Assert
        with (
            stubber,
            pytest.raises(
                botocore.exceptions.ClientError,
                match=r"An error occurred \(UnauthorizedOperation\) when calling the DescribeInstances operation: "
                r"You are not authorized to perform this operation",
            ),
        ):
            detect_instance_platform("i-0123456789abcdef0", session=session)


class Test_wait_for_instance_ready:
    def test_invalid_instance_id(self) -> None:
        # Act & Assert
        with pytest.raises(InvalidInstanceIdError, match=r"Invalid EC2 instance ID: 'not-an-id'"):
            wait_for_instance_ready("not-an-id", checker=mock.MagicMock())

    def test_wait_with_checker_success(self) -> None:
        # Arrange
        mock_checker = mock.MagicMock(return_value=True)

        # Act
        with mock.patch("time.sleep"):
            result = wait_for_instance_ready("i-0123456789abcdef0", checker=mock_checker, max_attempts=3)

        # Assert
        assert result is True
        mock_checker.assert_called_once_with("i-0123456789abcdef0", session=mock.ANY)

    def test_wait_with_custom_checker_multiple_attempts(self) -> None:
        # Arrange
        mock_checker = mock.MagicMock(side_effect=[False, True])

        # Act
        with mock.patch("time.sleep"):
            result = wait_for_instance_ready(
                "i-0123456789abcdef0",
                max_attempts=3,
                delay=0.1,
                checker=mock_checker,
            )

        # Assert
        assert result is True
        assert mock_checker.call_count == 2

    def test_wait_with_custom_checker_max_attempts_exceeded(self) -> None:
        # Arrange
        mock_checker = mock.MagicMock(return_value=False)

        # Act & Assert
        with (
            mock.patch("time.sleep"),
            pytest.raises(InstanceNotReadyError, match=r"failed to become ready after 2 attempts"),
        ):
            wait_for_instance_ready(
                "i-0123456789abcdef0",
                max_attempts=2,
                delay=0.1,
                checker=mock_checker,
            )

    def test_wait_checker_raises_exception_retried(self) -> None:
        # Arrange
        mock_checker = mock.MagicMock(side_effect=[RuntimeError("Transient network glitch"), True])

        # Act
        with mock.patch("time.sleep"):
            result = wait_for_instance_ready(
                "i-0123456789abcdef0",
                max_attempts=3,
                delay=0.1,
                checker=mock_checker,
            )

        # Assert
        assert result is True
        assert mock_checker.call_count == 2

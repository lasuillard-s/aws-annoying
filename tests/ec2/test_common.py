from typing import Any

import pytest

from aws_annoying.ec2 import (
    InstanceNotFoundError,
    detect_instance_platform,
)

pytestmark = [
    pytest.mark.unit,
]


class Test_detect_instance_platform:
    def test_detect_linux(self) -> None:
        """Test detecting Linux platform from EC2 instance description."""
        # Arrange
        response: Any = {
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
        }

        # Act
        platform = detect_instance_platform(response, "i-0123456789abcdef0")

        # Assert
        assert platform == "linux"

    def test_detect_windows_from_platform_field(self) -> None:
        """Test detecting Windows platform from Platform field."""
        # Arrange
        response: Any = {
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
        }

        # Act
        platform = detect_instance_platform(response, "i-0123456789abcdef0")

        # Assert
        assert platform == "windows"

    def test_detect_windows_from_platform_details(self) -> None:
        """Test detecting Windows platform from PlatformDetails field."""
        # Arrange
        response: Any = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-0123456789abcdef0",
                            "PlatformDetails": "Windows Server 2022",
                        }
                    ]
                }
            ]
        }

        # Act
        platform = detect_instance_platform(response, "i-0123456789abcdef0")

        # Assert
        assert platform == "windows"

    def test_instance_not_found_empty_reservations(self) -> None:
        """Test error raised when reservations list is empty."""
        # Arrange
        response: Any = {"Reservations": []}

        # Act & Assert
        with pytest.raises(InstanceNotFoundError, match=r"Instance 'i-0123456789abcdef0' not found\."):
            detect_instance_platform(response, "i-0123456789abcdef0")

    def test_instance_not_found_empty_instances(self) -> None:
        """Test error raised when instances list in reservation is empty."""
        # Arrange
        response: Any = {"Reservations": [{"Instances": []}]}

        # Act & Assert
        with pytest.raises(InstanceNotFoundError, match=r"Instance 'i-0123456789abcdef0' not found\."):
            detect_instance_platform(response, "i-0123456789abcdef0")

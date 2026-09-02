from __future__ import annotations

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

        # Act & Assert
        platform = detect_instance_platform(response, "i-0123456789abcdef0")
        assert platform == "linux"

    def test_detect_windows_from_platform_field(self) -> None:
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

        # Act & Assert
        platform = detect_instance_platform(response, "i-0123456789abcdef0")
        assert platform == "windows"

    def test_detect_windows_from_platform_details(self) -> None:
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

        # Act & Assert
        platform = detect_instance_platform(response, "i-0123456789abcdef0")
        assert platform == "windows"

    def test_instance_not_found_empty_reservations(self) -> None:
        # Arrange
        response: Any = {"Reservations": []}

        # Act & Assert
        with pytest.raises(InstanceNotFoundError, match=r"Instance 'i-0123456789abcdef0' not found\."):
            detect_instance_platform(response, "i-0123456789abcdef0")

    def test_instance_not_found_empty_instances(self) -> None:
        # Arrange
        response: Any = {"Reservations": [{"Instances": []}]}

        # Act & Assert
        with pytest.raises(InstanceNotFoundError, match=r"Instance 'i-0123456789abcdef0' not found\."):
            detect_instance_platform(response, "i-0123456789abcdef0")

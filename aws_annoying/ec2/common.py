from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from .errors import InstanceNotFoundError

if TYPE_CHECKING:
    from mypy_boto3_ec2.type_defs import DescribeInstancesResultTypeDef

INSTANCE_ID_PATTERN = re.compile(r"^(?:i|mi)-[0-9a-fA-F]{8,17}$")


def is_valid_instance_id(instance_id: str) -> bool:
    """Check if the given string is a valid EC2 instance ID format.

    Args:
        instance_id: The EC2 instance ID to validate.

    Returns:
        True if valid EC2 instance ID format, False otherwise.
    """
    return bool(INSTANCE_ID_PATTERN.match(instance_id))


def detect_instance_platform(
    response: DescribeInstancesResultTypeDef,
    instance_id: str,
) -> Literal["linux", "windows"]:
    """Detect whether an EC2 instance is running Windows or Linux from describe response.

    Args:
        response: The response dictionary from describe_instances.
        instance_id: The ID of the EC2 instance.

    Returns:
        'windows' if the instance is running Windows, otherwise 'linux'.

    Raises:
        InstanceNotFoundError: If the instance is not found in the response.
    """
    reservations = response.get("Reservations", [])
    if not reservations or not reservations[0].get("Instances"):
        msg = f"Instance '{instance_id}' not found."
        raise InstanceNotFoundError(msg)

    # Determine the platform based on the instance's Platform and PlatformDetails attributes
    instance = reservations[0]["Instances"][0]
    platform = instance.get("Platform", "")  # "windows" for Windows instances, absent for Linux
    platform_details = instance.get("PlatformDetails", "")

    if "windows" in platform.lower() or "windows" in platform_details.lower():
        return "windows"

    return "linux"

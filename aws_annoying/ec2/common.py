from __future__ import annotations

import re
from typing import Literal, Optional

import boto3
import botocore.exceptions

from .errors import InstanceNotFoundError

INSTANCE_ID_PATTERN = re.compile(r"^m?i-[0-9a-zA-Z]+$")


def is_valid_instance_id(instance_id: str) -> bool:
    """Check if the given string is a valid EC2 instance ID format.

    Args:
        instance_id: The EC2 instance ID to validate.

    Returns:
        True if valid EC2 instance ID format, False otherwise.
    """
    return bool(INSTANCE_ID_PATTERN.match(instance_id))


def detect_instance_platform(
    instance_id: str,
    *,
    session: Optional[boto3.session.Session] = None,
) -> Literal["linux", "windows"]:
    """Detect whether an EC2 instance is running Windows or Linux.

    Args:
        instance_id: The ID of the EC2 instance.
        session: Optional boto3 session to use.

    Returns:
        'windows' if the instance is running Windows, otherwise 'linux'.

    Raises:
        InstanceNotFoundError: If the instance is not found in EC2.

    Required IAM Permissions:

    - `ec2:DescribeInstances`
    """
    session = session or boto3.session.Session()
    ec2 = session.client("ec2")

    # Check if the instance exists and retrieve its platform information
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
    except botocore.exceptions.ClientError as err:
        if err.response.get("Error", {}).get("Code") == "InvalidInstanceID.NotFound":
            msg = f"Instance '{instance_id}' not found."
            raise InstanceNotFoundError(msg) from err

        raise

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

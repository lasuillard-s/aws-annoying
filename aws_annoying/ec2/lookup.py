from __future__ import annotations

from typing import Optional

import boto3

from .common import is_valid_instance_id
from .errors import MultipleInstancesFoundError


def get_instance_id_by_name(
    name_or_id: str,
    *,
    session: Optional[boto3.session.Session] = None,
    expect_one: bool = False,
) -> str | None:
    """Get the EC2 instance ID by name or ID.

    If name_or_id already matches an EC2 instance ID pattern, it is returned directly.
    Otherwise, instances are searched by the 'Name' tag.

    Args:
        name_or_id: The name or ID of the EC2 instance.
        session: The boto3 session to use. If not provided, a new session will be created.
        expect_one: Whether to raise an exception if multiple instances are found.

    Returns:
        The instance ID if found, otherwise `None`.

    Raises:
        MultipleInstancesFoundError: If `expect_one` is True and multiple instances match.

    Required IAM Permissions:

    - `ec2:DescribeInstances`
    """
    if is_valid_instance_id(name_or_id):
        return name_or_id

    session = session or boto3.session.Session()
    ec2 = session.client("ec2")

    response = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [name_or_id]}])
    instances = [
        instance for reservation in response.get("Reservations", []) for instance in reservation.get("Instances", [])
    ]
    if not instances:
        return None

    if expect_one and len(instances) > 1:
        msg = f"Multiple instances found with name '{name_or_id}' ({len(instances)} instances)."
        raise MultipleInstancesFoundError(msg)

    return str(instances[0]["InstanceId"])

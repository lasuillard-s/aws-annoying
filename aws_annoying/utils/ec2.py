from __future__ import annotations

import re

import boto3


def get_instance_id_by_name(name_or_id: str, *, session: boto3.session.Session | None = None) -> str | None:
    """Get the EC2 instance ID by name or ID.

    Be aware that this function will only return the first instance found
    with the given name, no matter how many instances are found.

    Args:
        name_or_id: The name or ID of the EC2 instance.
        session: The boto3 session to use. If not provided, a new session will be created.

    Returns:
        The instance ID if found, otherwise `None`.
    """
    if re.match(r"^m?i-[0-9a-f]+$", name_or_id):
        return name_or_id

    session = session or boto3.session.Session()
    ec2 = session.client("ec2")

    response = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [name_or_id]}])
    reservations = response["Reservations"]
    if not reservations or not reservations[0]["Instances"]:
        return None

    instances = reservations[0]["Instances"]
    return str(instances[0]["InstanceId"])

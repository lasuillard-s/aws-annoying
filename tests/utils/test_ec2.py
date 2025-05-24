from __future__ import annotations

import re

import boto3
import pytest

from aws_annoying.utils.ec2 import get_instance_id_by_name

pytestmark = [
    pytest.mark.unit,
    pytest.mark.usefixtures("use_moto"),
]


class Test_get_instance_id_by_name:
    def test_single_instance(self) -> None:
        # Arrange
        ec2 = boto3.client("ec2")
        ec2.run_instances(
            ImageId="ami-12345678",
            InstanceType="t2.micro",
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "my-instance"}]}],
        )

        # Act
        instance_id = get_instance_id_by_name("my-instance")

        # Assert
        assert len(ec2.describe_instances()["Reservations"]) == 1
        assert instance_id is not None
        assert re.match(r"^i-[0-9a-f]+$", instance_id) is not None

    def test_if_multiple_instances_exists(self) -> None:
        # Arrange
        ec2 = boto3.client("ec2")
        for _ in range(3):
            ec2.run_instances(
                ImageId="ami-12345678",
                InstanceType="t2.micro",
                MinCount=1,
                MaxCount=1,
                TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "my-instance"}]}],
            )

        # Act
        instance_id = get_instance_id_by_name("my-instance")

        # Assert
        assert len(ec2.describe_instances()["Reservations"]) == 3
        assert instance_id is not None
        assert re.match(r"^i-[0-9a-f]+$", instance_id) is not None

    def test_if_no_instance(self) -> None:
        # Arrange
        ec2 = boto3.client("ec2")

        # Act
        instance_id = get_instance_id_by_name("my-instance")

        # Assert
        assert len(ec2.describe_instances()["Reservations"]) == 0
        assert instance_id is None

from __future__ import annotations

import re

import boto3
import pytest

from aws_annoying.ec2 import (
    MultipleInstancesFoundError,
    get_instance_id_by_name,
    is_valid_instance_id,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.usefixtures("use_moto"),
]


class Test_is_valid_instance_id:
    @pytest.mark.parametrize(
        ("instance_id", "expected"),
        [
            ("i-12345678", True),
            ("i-0123456789abcdef0", True),
            ("i-1a2b3c4d5e6f7a8b9", True),
            ("i-AbCdEf0123456789", True),
            ("mi-0123456789abcdef0", True),
            ("mi-12345678", True),
            ("my-instance", False),
            ("i-", False),
            ("", False),
            ("vol-0123456789abcdef0", False),
        ],
    )
    def test_validation(self, instance_id: str, *, expected: bool) -> None:
        # Act & Assert
        assert is_valid_instance_id(instance_id) is expected


class Test_get_instance_id_by_name:
    def test_get_by_name(self) -> None:
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
        assert re.match(r"^i-[0-9a-zA-Z]+$", instance_id) is not None

    def test_get_by_name_not_found(self) -> None:
        # Arrange
        ec2 = boto3.client("ec2")

        # Act
        instance_id = get_instance_id_by_name("my-instance")

        # Assert
        assert len(ec2.describe_instances()["Reservations"]) == 0
        assert instance_id is None

    def test_get_by_instance_id(self) -> None:
        # Arrange
        ec2 = boto3.client("ec2")
        response = ec2.run_instances(
            ImageId="ami-12345678",
            InstanceType="t2.micro",
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "my-instance"}]}],
        )
        instance_id = response["Instances"][0]["InstanceId"]

        # Act
        fetched_instance_id = get_instance_id_by_name(instance_id)

        # Assert
        assert len(ec2.describe_instances()["Reservations"]) == 1
        assert fetched_instance_id == instance_id

    def test_if_multiple_instances_exists_default(self) -> None:
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
        assert re.match(r"^i-[0-9a-zA-Z]+$", instance_id) is not None

    def test_if_multiple_instances_exists_expect_one(self) -> None:
        # Arrange
        ec2 = boto3.client("ec2")
        for _ in range(2):
            ec2.run_instances(
                ImageId="ami-12345678",
                InstanceType="t2.micro",
                MinCount=1,
                MaxCount=1,
                TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "my-instance"}]}],
            )

        # Act & Assert
        with pytest.raises(MultipleInstancesFoundError, match=r"Multiple instances found with name 'my-instance'"):
            get_instance_id_by_name("my-instance", expect_one=True)

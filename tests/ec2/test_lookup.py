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


def test_is_valid_instance_id() -> None:
    # Valid instance IDs
    assert is_valid_instance_id("i-12345678")
    assert is_valid_instance_id("i-0123456789abcdef0")
    assert is_valid_instance_id("i-1a2b3c4d5e6f7a8b9")
    assert is_valid_instance_id("i-AbCdEf0123456789")
    assert is_valid_instance_id("mi-0123456789abcdef0")
    assert is_valid_instance_id("mi-12345678")

    # Invalid instance IDs
    assert not is_valid_instance_id("i-z")
    assert not is_valid_instance_id("i-1234567z")
    assert not is_valid_instance_id("mi-zzzzzzzz")
    assert not is_valid_instance_id("i-1234567")
    assert not is_valid_instance_id("i-0123456789abcdef012")
    assert not is_valid_instance_id("my-instance")
    assert not is_valid_instance_id("i-")
    assert not is_valid_instance_id("")
    assert not is_valid_instance_id("vol-0123456789abcdef0")


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
        instance_id = get_instance_id_by_name("my-instance", client=ec2)

        # Assert
        assert len(ec2.describe_instances()["Reservations"]) == 1
        assert instance_id is not None
        assert re.match(r"^i-[0-9a-zA-Z]+$", instance_id) is not None

    def test_get_by_name_not_found(self) -> None:
        # Arrange
        ec2 = boto3.client("ec2")

        # Act
        instance_id = get_instance_id_by_name("my-instance", client=ec2)

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
        fetched_instance_id = get_instance_id_by_name(instance_id, client=ec2)

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
        instance_id = get_instance_id_by_name("my-instance", client=ec2)

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
            get_instance_id_by_name("my-instance", client=ec2, expect_one=True)

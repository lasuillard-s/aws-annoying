from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

import boto3
import pytest
from typer.testing import CliRunner

from aws_annoying.cli.main import app
from tests.cli._helpers import normalize_console_output

if TYPE_CHECKING:
    from pytest_snapshot.plugin import Snapshot

runner = CliRunner()

pytestmark = [
    pytest.mark.unit,
    pytest.mark.usefixtures("use_moto"),
]


def test_invalid_instance_id(snapshot: Snapshot) -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "invalid-instance-name",
        ],
    )

    # Assert
    assert result.exit_code == 1
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""


def test_invalid_document_parameters_json(snapshot: Snapshot) -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--document-parameters",
            "not-valid-json",
        ],
    )

    # Assert
    assert result.exit_code == 2
    assert result.stdout == ""
    snapshot.assert_match(normalize_console_output(result.stderr), "stderr.txt")


def test_document_name_without_parameters() -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--document-name",
            "AWS-RunShellScript",
        ],
    )

    # Assert
    assert result.exit_code == 2
    assert "Both --document-name and --document-parameters must be provided together." in normalize_console_output(
        result.stderr
    )


def test_document_parameters_without_name() -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--document-parameters",
            '{"commands": ["echo ready"]}',
        ],
    )

    # Assert
    assert result.exit_code == 2
    assert "Both --document-name and --document-parameters must be provided together." in normalize_console_output(
        result.stderr
    )


def test_invalid_document_parameters_not_dict(snapshot: Snapshot) -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--document-name",
            "AWS-RunShellScript",
            "--document-parameters",
            '["not", "a", "dict"]',
        ],
    )

    # Assert
    assert result.exit_code == 2
    assert result.stdout == ""
    snapshot.assert_match(normalize_console_output(result.stderr), "stderr.txt")


@pytest.mark.parametrize(
    "invalid_parameters",
    [
        "null",
        "123",
        '"a string"',
        "true",
    ],
)
def test_invalid_document_parameters_non_dict_types(invalid_parameters: str) -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--document-name",
            "AWS-RunShellScript",
            "--document-parameters",
            invalid_parameters,
        ],
    )

    # Assert
    assert result.exit_code == 2
    assert "Parameters must be a JSON object (key-value mapping)" in normalize_console_output(result.stderr)


def test_invalid_max_attempts_bound() -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--max-attempts",
            "0",
        ],
    )

    # Assert
    assert result.exit_code == 2
    assert "Invalid value for '--max-attempts': 0 is not in the range x>=1." in normalize_console_output(result.stderr)


def test_invalid_delay_bound() -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
            "--delay",
            "-1",
        ],
    )

    # Assert
    assert result.exit_code == 2
    assert "Invalid value for '--delay': -1.0 is not in the range x>=0.0." in result.stderr


def test_wait_for_ready_success_auto(snapshot: Snapshot) -> None:
    # Arrange
    ec2 = boto3.client("ec2")
    res = ec2.run_instances(
        ImageId="ami-12345678",
        InstanceType="t2.micro",
        MinCount=1,
        MaxCount=1,
    )
    instance_id = res["Instances"][0]["InstanceId"]

    # Act
    with mock.patch("time.sleep"):
        result = runner.invoke(
            app,
            [
                "ec2",
                "wait-for-ready",
                "--instance-id",
                instance_id,
                "--max-attempts",
                "5",
                "--delay",
                "10",
            ],
        )

    # Assert
    assert result.exit_code == 0
    snapshot.assert_match(
        normalize_console_output(result.stdout, replace={instance_id: "i-0123456789abcdef0"}),
        "stdout.txt",
    )
    assert result.stderr == ""


def test_wait_for_ready_success_windows(snapshot: Snapshot) -> None:
    # Arrange
    ec2 = boto3.client("ec2")
    res = ec2.run_instances(
        ImageId="ami-12345678",
        InstanceType="t2.micro",
        MinCount=1,
        MaxCount=1,
    )
    instance_id = res["Instances"][0]["InstanceId"]

    # Act
    with mock.patch("time.sleep"):
        result = runner.invoke(
            app,
            [
                "ec2",
                "wait-for-ready",
                "--instance-id",
                instance_id,
                "--platform",
                "windows",
            ],
        )

    # Assert
    assert result.exit_code == 0
    snapshot.assert_match(
        normalize_console_output(result.stdout, replace={instance_id: "i-0123456789abcdef0"}),
        "stdout.txt",
    )
    assert result.stderr == ""


def test_wait_for_ready_custom_document_with_parameters(snapshot: Snapshot) -> None:
    # Arrange
    ec2 = boto3.client("ec2")
    res = ec2.run_instances(
        ImageId="ami-12345678",
        InstanceType="t2.micro",
        MinCount=1,
        MaxCount=1,
    )
    instance_id = res["Instances"][0]["InstanceId"]

    # Act
    with mock.patch("time.sleep"):
        result = runner.invoke(
            app,
            [
                "ec2",
                "wait-for-ready",
                "--instance-id",
                instance_id,
                "--document-name",
                "AWS-RunShellScript",
                "--document-parameters",
                '{"commands": ["echo ready"]}',
            ],
        )

    # Assert
    assert result.exit_code == 0
    snapshot.assert_match(
        normalize_console_output(result.stdout, replace={instance_id: "i-0123456789abcdef0"}),
        "stdout.txt",
    )
    assert result.stderr == ""


def test_wait_for_ready_not_found_failure() -> None:
    # Act
    result = runner.invoke(
        app,
        [
            "ec2",
            "wait-for-ready",
            "--instance-id",
            "i-0123456789abcdef0",
        ],
    )

    # Assert
    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr == ""


def test_wait_for_ready_not_ready_failure(snapshot: Snapshot) -> None:
    # Arrange
    ec2 = boto3.client("ec2")
    res = ec2.run_instances(
        ImageId="ami-12345678",
        InstanceType="t2.micro",
        MinCount=1,
        MaxCount=1,
    )
    instance_id = res["Instances"][0]["InstanceId"]

    # Act
    with (
        mock.patch("time.sleep"),
        mock.patch(
            "aws_annoying.cli.ec2.wait_for_ready.make_ssm_checker",
            return_value=mock.MagicMock(return_value=False),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "ec2",
                "wait-for-ready",
                "--instance-id",
                instance_id,
                "--platform",
                "linux",
                "--max-attempts",
                "2",
                "--delay",
                "0.1",
            ],
        )

    # Assert
    assert result.exit_code == 1
    snapshot.assert_match(
        normalize_console_output(result.stdout, replace={instance_id: "i-0123456789abcdef0"}),
        "stdout.txt",
    )
    assert result.stderr == ""

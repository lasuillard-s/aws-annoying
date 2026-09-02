from unittest import mock

import boto3
import pytest
from inline_snapshot import snapshot
from typer.testing import CliRunner

from aws_annoying._cli.main import app
from tests._cli._helpers import normalize_console_output

runner = CliRunner()

pytestmark = [
    pytest.mark.unit,
    pytest.mark.usefixtures("use_moto"),
]


def test_invalid_instance_id() -> None:
    """Test that specifying an invalid EC2 instance ID returns an error."""
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
    assert normalize_console_output(result.stdout) == snapshot("🚨 Invalid EC2 instance ID 'invalid-instance-name'")
    assert result.stderr == ""


def test_invalid_document_parameters_json() -> None:
    """Test that providing invalid JSON for document parameters causes a CLI error."""
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
    assert normalize_console_output(result.stderr) == snapshot("""\
Usage: root ec2 wait-for-ready [OPTIONS]
Try 'root ec2 wait-for-ready --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Invalid value for '--document-parameters': Failed to parse JSON argument                                                                                                                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯\
""")


def test_document_name_without_parameters() -> None:
    """Test that providing document name without parameters raises an error."""
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
    """Test that providing document parameters without name raises an error."""
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


def test_invalid_document_parameters_not_dict() -> None:
    """Test that document parameters passed as a JSON array instead of an object raises an error."""
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
    assert normalize_console_output(result.stderr) == snapshot("""\
Usage: root ec2 wait-for-ready [OPTIONS]
Try 'root ec2 wait-for-ready --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Invalid value for '--document-parameters': Parameters must be a JSON object (key-value mapping)                                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯\
""")


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
    """Test that non-dict JSON document parameters raise a validation error."""
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
    """Test that specifying max attempts less than 1 raises a validation error."""
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
    """Test that specifying a negative delay raises a validation error."""
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
    assert "Invalid value for '--delay': -1.0 is not in the range x>=0.0." in normalize_console_output(result.stderr)


def test_wait_for_ready_success_auto() -> None:
    """Test successfully waiting for an EC2 instance to become ready with auto platform detection."""
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
    assert normalize_console_output(result.stdout, replace={instance_id: "i-0123456789abcdef0"}) == snapshot("""\
🔔 Waiting for instance i-0123456789abcdef0 to be ready...
🔔 Attempt 1/5...
🔔 Instance i-0123456789abcdef0 is ready.\
""")
    assert result.stderr == ""


def test_wait_for_ready_success_windows() -> None:
    """Test successfully waiting for an EC2 instance with explicit windows platform."""
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
    assert normalize_console_output(result.stdout, replace={instance_id: "i-0123456789abcdef0"}) == snapshot("""\
🔔 Waiting for instance i-0123456789abcdef0 to be ready...
🔔 Attempt 1/10...
🔔 Instance i-0123456789abcdef0 is ready.\
""")
    assert result.stderr == ""


def test_wait_for_ready_custom_document_with_parameters() -> None:
    """Test successfully waiting for an EC2 instance using a custom SSM document and parameters."""
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
    assert normalize_console_output(result.stdout, replace={instance_id: "i-0123456789abcdef0"}) == snapshot("""\
🔔 Waiting for instance i-0123456789abcdef0 to be ready...
🔔 Attempt 1/10...
🔔 Instance i-0123456789abcdef0 is ready.\
""")
    assert result.stderr == ""


def test_wait_for_ready_not_found_failure() -> None:
    """Test waiting for a non-existent instance fails with exit code 1."""
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


def test_wait_for_ready_not_ready_failure() -> None:
    """Test waiting for an instance fails if it does not become ready within max attempts."""
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
            "aws_annoying._cli.ec2.wait_for_ready.InstanceReadinessWaiter.check_ready",
            return_value=False,
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
    assert normalize_console_output(result.stdout, replace={instance_id: "i-0123456789abcdef0"}) == snapshot("""\
🔔 Waiting for instance i-0123456789abcdef0 to be ready...
🔔 Attempt 1/2...
🔔 Attempt 2/2...
🚨 Maximum attempts reached. Instance i-0123456789abcdef0 is not ready.
🚨 Failed waiting for instance to be ready: Instance 'i-0123456789abcdef0' failed to become ready after 2 attempts.\
""")
    assert result.stderr == ""

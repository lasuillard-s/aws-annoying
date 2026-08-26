from __future__ import annotations

import os
from unittest import mock

import boto3
import pytest
from typer.testing import CliRunner

from aws_annoying.cli.main import app
from aws_annoying.session_manager import SessionManager

runner = CliRunner()

pytestmark = [
    pytest.mark.unit,
    pytest.mark.usefixtures("use_moto"),
]


def test_start_with_explicit_ec2_target_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """The command should resolve EC2 target ID and start session."""
    # Arrange
    ec2 = boto3.client("ec2")
    res = ec2.run_instances(ImageId="ami-12345678", InstanceType="t2.micro", MinCount=1, MaxCount=1)
    instance_id = res["Instances"][0]["InstanceId"]

    mock_execvp = mock.MagicMock()
    mock_build_command = mock.MagicMock(return_value=["session-manager-plugin", instance_id])
    monkeypatch.setattr(os, "execvp", mock_execvp)
    monkeypatch.setattr(SessionManager, "build_command", mock_build_command)

    # Act
    result = runner.invoke(app, ["session-manager", "start", "--target", instance_id, "--reason", "test reason"])

    # Assert
    assert result.exit_code == 0
    mock_build_command.assert_called_once_with(
        target=instance_id,
        document_name="SSM-SessionManagerRunShell",
        parameters={},
        reason="test reason",
    )
    mock_execvp.assert_called_once_with("session-manager-plugin", ["session-manager-plugin", instance_id])


def test_start_with_explicit_ec2_target_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """The command should resolve EC2 target by name tag and start session."""
    # Arrange
    ec2 = boto3.client("ec2")
    res = ec2.run_instances(
        ImageId="ami-12345678",
        InstanceType="t2.micro",
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "prod-web"}]}],
    )
    instance_id = res["Instances"][0]["InstanceId"]

    mock_execvp = mock.MagicMock()
    mock_build_command = mock.MagicMock(return_value=["session-manager-plugin", instance_id])
    monkeypatch.setattr(os, "execvp", mock_execvp)
    monkeypatch.setattr(SessionManager, "build_command", mock_build_command)

    # Act
    result = runner.invoke(app, ["session-manager", "start", "--target", "prod-web"])

    # Assert
    assert result.exit_code == 0
    mock_build_command.assert_called_once_with(
        target=instance_id,
        document_name="SSM-SessionManagerRunShell",
        parameters={},
        reason="",
    )
    mock_execvp.assert_called_once_with("session-manager-plugin", ["session-manager-plugin", instance_id])


def test_start_with_explicit_ec2_target_not_found() -> None:
    """The command should exit with code 1 if instance name not found."""
    # Act
    result = runner.invoke(app, ["session-manager", "start", "--target", "non-existent-instance"])

    # Assert
    assert result.exit_code == 1


def test_start_with_explicit_ecs_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """The command should start session directly for ecs: target."""
    mock_execvp = mock.MagicMock()
    mock_build_command = mock.MagicMock(return_value=["session-manager-plugin", "ecs:target"])
    monkeypatch.setattr(os, "execvp", mock_execvp)
    monkeypatch.setattr(SessionManager, "build_command", mock_build_command)

    ecs_target = "ecs:mycluster_mytask_myruntimeid"

    # Act
    result = runner.invoke(app, ["session-manager", "start", "--target", ecs_target])

    # Assert
    assert result.exit_code == 0
    mock_build_command.assert_called_once_with(
        target=ecs_target,
        document_name="SSM-SessionManagerRunShell",
        parameters={},
        reason="",
    )
    mock_execvp.assert_called_once_with("session-manager-plugin", ["session-manager-plugin", "ecs:target"])


def test_start_interactive_invoked(monkeypatch: pytest.MonkeyPatch) -> None:
    """The command should invoke interactive start handler when target is None."""
    mock_execvp = mock.MagicMock()
    mock_build_command = mock.MagicMock(return_value=["session-manager-plugin", "ecs:cluster_task_container"])
    monkeypatch.setattr(os, "execvp", mock_execvp)
    monkeypatch.setattr(SessionManager, "build_command", mock_build_command)
    monkeypatch.setattr(
        "aws_annoying.cli.session_manager.start._handle_interactive_start",
        mock.MagicMock(return_value="ecs:cluster_task_container"),
    )

    # Act
    result = runner.invoke(app, ["session-manager", "start"])

    # Assert
    assert result.exit_code == 0
    mock_build_command.assert_called_once_with(
        target="ecs:cluster_task_container",
        document_name="SSM-SessionManagerRunShell",
        parameters={},
        reason="",
    )
    mock_execvp.assert_called_once()

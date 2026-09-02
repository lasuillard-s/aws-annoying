from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

import boto3
import pytest
from typer.testing import CliRunner

from aws_annoying._cli.main import app
from aws_annoying.utils.tcp_proxy import Address
from tests._cli._helpers import normalize_console_output

if TYPE_CHECKING:
    from pytest_snapshot.plugin import Snapshot

runner = CliRunner()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("use_moto"),
]


def test_instance_not_found(snapshot: Snapshot) -> None:
    # Arrange & Act
    result = runner.invoke(
        app,
        [
            "session-manager",
            "port-forward",
            "--through",
            "nonexistent-instance",
            "--local-port",
            "8080",
            "--remote-host",
            "10.0.0.1",
            "--remote-port",
            "80",
            "--reason",
            "Testing port forwarding",
        ],
    )

    # Assert
    assert result.exit_code == 1
    snapshot.assert_match(normalize_console_output(result.stdout), "stdout.txt")
    assert result.stderr == ""


def test_port_forward_localhost(snapshot: Snapshot) -> None:
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

    mock_proc = mock.MagicMock()
    mock_proc.wait.return_value = 0

    with (
        mock.patch(
            "aws_annoying.session_manager.SessionManager.build_command",
            return_value=["session-manager-plugin", "arg1"],
        ) as mock_build_cmd,
        mock.patch("subprocess.Popen", return_value=mock_proc) as mock_popen,
    ):
        # Act
        result = runner.invoke(
            app,
            [
                "session-manager",
                "port-forward",
                "--through",
                "my-instance",
                "--local-port",
                "8080",
                "--remote-host",
                "10.0.0.1",
                "--remote-port",
                "80",
                "--reason",
                "Testing port forwarding",
            ],
        )

    # Assert
    assert result.exit_code == 0
    mock_build_cmd.assert_called_once_with(
        target=instance_id,
        document_name="AWS-StartPortForwardingSessionToRemoteHost",
        parameters={
            "host": ["10.0.0.1"],
            "portNumber": ["80"],
            "localPortNumber": ["8080"],
        },
        reason="Testing port forwarding",
    )
    mock_popen.assert_called_once()
    mock_proc.wait.assert_called_once()
    snapshot.assert_match(
        normalize_console_output(result.stdout, replace={instance_id: "<instance_id>"}),
        "stdout.txt",
    )
    assert result.stderr == ""


def test_port_forward_non_localhost(snapshot: Snapshot) -> None:
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

    mock_proc = mock.MagicMock()
    mock_proc.wait.return_value = 0

    with (
        mock.patch("aws_annoying._cli.session_manager.port_forward.get_free_port", return_value=54321),
        mock.patch("aws_annoying._cli.session_manager.port_forward.TCPProxy") as mock_proxy_cls,
        mock.patch(
            "aws_annoying.session_manager.SessionManager.build_command",
            return_value=["session-manager-plugin", "arg1"],
        ) as mock_build_cmd,
        mock.patch("subprocess.Popen", return_value=mock_proc) as mock_popen,
    ):
        mock_proxy = mock.MagicMock()
        mock_proxy_cls.return_value = mock_proxy

        # Act
        result = runner.invoke(
            app,
            [
                "session-manager",
                "port-forward",
                "--local-host",
                "0.0.0.0",  # noqa: S104
                "--through",
                "my-instance",
                "--local-port",
                "8080",
                "--remote-host",
                "10.0.0.1",
                "--remote-port",
                "80",
                "--reason",
                "Testing port forwarding",
            ],
        )

    # Assert
    assert result.exit_code == 0
    mock_proxy_cls.assert_called_once_with(Address("0.0.0.0", 8080), Address("127.0.0.1", 54321))  # noqa: S104
    mock_proxy.start.assert_called_once()
    mock_build_cmd.assert_called_once_with(
        target=instance_id,
        document_name="AWS-StartPortForwardingSessionToRemoteHost",
        parameters={
            "host": ["10.0.0.1"],
            "portNumber": ["80"],
            "localPortNumber": ["54321"],
        },
        reason="Testing port forwarding",
    )
    mock_popen.assert_called_once()
    mock_proc.wait.assert_called_once()
    mock_proxy.stop.assert_called_once()
    snapshot.assert_match(
        normalize_console_output(result.stdout, replace={instance_id: "<instance_id>"}),
        "stdout.txt",
    )
    assert result.stderr == ""


def test_port_forward_exit_code_failure() -> None:
    # Arrange
    ec2 = boto3.client("ec2")
    ec2.run_instances(
        ImageId="ami-12345678",
        InstanceType="t2.micro",
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "my-instance"}]}],
    )

    mock_proc = mock.MagicMock()
    mock_proc.wait.return_value = 42

    with (
        mock.patch(
            "aws_annoying.session_manager.SessionManager.build_command",
            return_value=["session-manager-plugin", "arg1"],
        ),
        mock.patch("subprocess.Popen", return_value=mock_proc),
    ):
        # Act
        result = runner.invoke(
            app,
            [
                "session-manager",
                "port-forward",
                "--through",
                "my-instance",
                "--local-port",
                "8080",
                "--remote-host",
                "10.0.0.1",
                "--remote-port",
                "80",
            ],
        )

    # Assert
    assert result.exit_code == 42

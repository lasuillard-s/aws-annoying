from __future__ import annotations

import os
from unittest import mock

import boto3
import pytest
import typer
from prompt_toolkit.key_binding import KeyBindings
from typer.testing import CliRunner

from aws_annoying.cli.main import app
from aws_annoying.cli.session_manager.start import (
    _get_cluster_name,
    _get_service_name,
    _get_task_id,
    _handle_interactive_start,
    _prompt_select,
    _select_ec2_instance,
    _select_ecs_cluster,
    _select_ecs_container_in_task,
    _select_ecs_service,
    _select_ecs_task,
)
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
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Env", "Value": "prod"},
                    {"Key": "Name", "Value": "prod-web"},
                ],
            }
        ],
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


class Test_select_ec2_instance:
    def test_select_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ec2 = boto3.client("ec2")
        res = ec2.run_instances(
            ImageId="ami-12345678",
            InstanceType="t2.micro",
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Env", "Value": "prod"},
                        {"Key": "Name", "Value": "web-server"},
                    ],
                }
            ],
        )
        instance_id = res["Instances"][0]["InstanceId"]

        mock_prompt = mock.MagicMock(return_value=instance_id)
        monkeypatch.setattr("aws_annoying.cli.session_manager.start._prompt_select", mock_prompt)

        selected = _select_ec2_instance(ec2)
        assert selected == instance_id
        mock_prompt.assert_called_once()

    def test_select_empty(self) -> None:
        ec2 = boto3.client("ec2")
        selected = _select_ec2_instance(ec2)
        assert selected is None


class Test_select_ecs_cluster:
    def test_select_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ecs = boto3.client("ecs")
        cluster_arn = ecs.create_cluster(clusterName="main-cluster")["cluster"]["clusterArn"]

        mock_prompt = mock.MagicMock(return_value=cluster_arn)
        monkeypatch.setattr("aws_annoying.cli.session_manager.start._prompt_select", mock_prompt)

        selected = _select_ecs_cluster(ecs)
        assert selected == cluster_arn
        mock_prompt.assert_called_once()

    def test_select_empty(self) -> None:
        ecs = boto3.client("ecs")
        selected = _select_ecs_cluster(ecs)
        assert selected is None


class Test_select_ecs_service:
    def test_select_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ecs = boto3.client("ecs")
        cluster_arn = ecs.create_cluster(clusterName="main-cluster")["cluster"]["clusterArn"]
        task_def = ecs.register_task_definition(
            family="my-task",
            containerDefinitions=[{"name": "app", "image": "app:latest", "memory": 512, "cpu": 256}],
        )
        service_arn = ecs.create_service(
            cluster=cluster_arn,
            serviceName="web-service",
            taskDefinition=task_def["taskDefinition"]["taskDefinitionArn"],
            desiredCount=1,
        )["service"]["serviceArn"]

        mock_prompt = mock.MagicMock(return_value=service_arn)
        monkeypatch.setattr("aws_annoying.cli.session_manager.start._prompt_select", mock_prompt)

        selected = _select_ecs_service(ecs, cluster_arn)
        assert selected == service_arn

    def test_select_empty(self) -> None:
        ecs = boto3.client("ecs")
        cluster_arn = ecs.create_cluster(clusterName="empty-cluster")["cluster"]["clusterArn"]
        selected = _select_ecs_service(ecs, cluster_arn)
        assert selected is None


class Test_select_ecs_task:
    def test_select_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ecs = boto3.client("ecs")
        cluster_arn = ecs.create_cluster(clusterName="main-cluster")["cluster"]["clusterArn"]
        task_def = ecs.register_task_definition(
            family="my-task",
            containerDefinitions=[{"name": "app", "image": "app:latest", "memory": 512, "cpu": 256}],
        )
        ecs.create_service(
            cluster=cluster_arn,
            serviceName="web-service",
            taskDefinition=task_def["taskDefinition"]["taskDefinitionArn"],
            desiredCount=1,
        )
        run_res = ecs.run_task(
            cluster=cluster_arn,
            taskDefinition=task_def["taskDefinition"]["taskDefinitionArn"],
            count=1,
            launchType="FARGATE",
        )
        task_arn = run_res["tasks"][0]["taskArn"]

        mock_prompt = mock.MagicMock(return_value=task_arn)
        monkeypatch.setattr("aws_annoying.cli.session_manager.start._prompt_select", mock_prompt)

        selected = _select_ecs_task(ecs, cluster_arn, "arn:aws:ecs:us-east-1:123456789012:service/web-service")
        assert selected == task_arn
        mock_prompt.assert_called_once()

    def test_select_empty(self) -> None:
        ecs = boto3.client("ecs")
        cluster_arn = ecs.create_cluster(clusterName="empty-cluster")["cluster"]["clusterArn"]
        selected = _select_ecs_task(
            ecs,
            cluster_arn,
            "arn:aws:ecs:us-east-1:123456789012:service/empty",
        )
        assert selected is None


class Test_select_ecs_container_in_task:
    def test_select_success_with_runtime_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ecs = boto3.client("ecs")
        cluster_arn = ecs.create_cluster(clusterName="main-cluster")["cluster"]["clusterArn"]
        task_def = ecs.register_task_definition(
            family="my-task",
            containerDefinitions=[{"name": "app", "image": "app:latest", "memory": 512, "cpu": 256}],
        )
        task_arn = ecs.run_task(
            cluster=cluster_arn,
            taskDefinition=task_def["taskDefinition"]["taskDefinitionArn"],
            count=1,
            launchType="FARGATE",
        )["tasks"][0]["taskArn"]

        monkeypatch.setattr(
            ecs,
            "describe_tasks",
            mock.MagicMock(
                return_value={
                    "tasks": [
                        {
                            "taskArn": task_arn,
                            "containers": [{"name": "app", "runtimeId": "container-runtime-123"}],
                        }
                    ]
                }
            ),
        )

        mock_prompt = mock.MagicMock(return_value="app")
        monkeypatch.setattr("aws_annoying.cli.session_manager.start._prompt_select", mock_prompt)

        selected = _select_ecs_container_in_task(ecs, cluster_arn, task_arn)
        assert selected == "container-runtime-123"

    def test_select_success_without_runtime_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ecs = boto3.client("ecs")
        cluster_arn = "arn:aws:ecs:us-east-1:123456789012:cluster/main-cluster"
        task_arn = "arn:aws:ecs:us-east-1:123456789012:task/task-123"

        monkeypatch.setattr(
            ecs,
            "describe_tasks",
            mock.MagicMock(
                return_value={
                    "tasks": [
                        {
                            "taskArn": task_arn,
                            "containers": [{"name": "sidecar"}],
                        }
                    ]
                }
            ),
        )

        mock_prompt = mock.MagicMock(return_value="sidecar")
        monkeypatch.setattr("aws_annoying.cli.session_manager.start._prompt_select", mock_prompt)

        selected = _select_ecs_container_in_task(ecs, cluster_arn, task_arn)
        assert selected == "sidecar"

    def test_select_cancelled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ecs = boto3.client("ecs")
        cluster_arn = "arn:aws:ecs:us-east-1:123456789012:cluster/main-cluster"
        task_arn = "arn:aws:ecs:us-east-1:123456789012:task/task-123"

        monkeypatch.setattr(
            ecs,
            "describe_tasks",
            mock.MagicMock(
                return_value={
                    "tasks": [
                        {
                            "taskArn": task_arn,
                            "containers": [{"name": "app"}],
                        }
                    ]
                }
            ),
        )

        mock_prompt = mock.MagicMock(return_value=None)
        monkeypatch.setattr("aws_annoying.cli.session_manager.start._prompt_select", mock_prompt)

        selected = _select_ecs_container_in_task(ecs, cluster_arn, task_arn)
        assert selected is None

    def test_select_no_tasks_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ecs = boto3.client("ecs")
        cluster_arn = "arn:aws:ecs:us-east-1:123456789012:cluster/main"
        task_arn = "arn:aws:ecs:us-east-1:123456789012:task/not-found"

        monkeypatch.setattr(ecs, "describe_tasks", mock.MagicMock(return_value={"tasks": []}))

        selected = _select_ecs_container_in_task(ecs, cluster_arn, task_arn)
        assert selected is None

    def test_select_no_containers_in_task(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ecs = boto3.client("ecs")
        cluster_arn = "arn:aws:ecs:us-east-1:123456789012:cluster/main"
        task_arn = "arn:aws:ecs:us-east-1:123456789012:task/task-123"

        monkeypatch.setattr(
            ecs,
            "describe_tasks",
            mock.MagicMock(return_value={"tasks": [{"taskArn": task_arn, "containers": []}]}),
        )

        selected = _select_ecs_container_in_task(ecs, cluster_arn, task_arn)
        assert selected is None


class Test_handle_interactive_start:
    def test_interactive_ec2_flow(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "aws_annoying.cli.session_manager.start._prompt_select",
            mock.MagicMock(return_value="ec2"),
        )
        monkeypatch.setattr(
            "aws_annoying.cli.session_manager.start._select_ec2_instance",
            mock.MagicMock(return_value="i-1234567890abcdef0"),
        )

        result = _handle_interactive_start()
        assert result == "i-1234567890abcdef0"

    def test_interactive_ecs_flow(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "aws_annoying.cli.session_manager.start._prompt_select",
            mock.MagicMock(return_value="ecs"),
        )
        monkeypatch.setattr(
            "aws_annoying.cli.session_manager.start._select_ecs_cluster",
            mock.MagicMock(return_value="arn:aws:ecs:us-east-1:123456789012:cluster/my-cluster"),
        )
        monkeypatch.setattr(
            "aws_annoying.cli.session_manager.start._select_ecs_service",
            mock.MagicMock(return_value="arn:aws:ecs:us-east-1:123456789012:service/my-service"),
        )
        monkeypatch.setattr(
            "aws_annoying.cli.session_manager.start._select_ecs_task",
            mock.MagicMock(return_value="arn:aws:ecs:us-east-1:123456789012:task/my-cluster/task-123"),
        )
        monkeypatch.setattr(
            "aws_annoying.cli.session_manager.start._select_ecs_container_in_task",
            mock.MagicMock(return_value="runtime-456"),
        )

        result = _handle_interactive_start()
        assert result == "ecs:my-cluster_task-123_runtime-456"

    def test_interactive_back_navigation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        target_type_mock = mock.MagicMock(side_effect=["ec2", "ecs", "ec2"])
        select_ec2_mock = mock.MagicMock(side_effect=[None, "i-99999999"])
        select_ecs_cluster_mock = mock.MagicMock(
            side_effect=["arn:aws:ecs:us-east-1:123456789012:cluster/cluster-1", None]
        )
        select_ecs_service_mock = mock.MagicMock(return_value=None)

        def prompt_dispatcher(title: str, *_args: object, **_kwargs: object) -> object:
            if "Target Type" in title:
                return target_type_mock()
            return None

        monkeypatch.setattr("aws_annoying.cli.session_manager.start._prompt_select", prompt_dispatcher)
        monkeypatch.setattr("aws_annoying.cli.session_manager.start._select_ec2_instance", select_ec2_mock)
        monkeypatch.setattr("aws_annoying.cli.session_manager.start._select_ecs_cluster", select_ecs_cluster_mock)
        monkeypatch.setattr("aws_annoying.cli.session_manager.start._select_ecs_service", select_ecs_service_mock)

        result = _handle_interactive_start()
        assert result == "i-99999999"

    def test_interactive_container_back_navigation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        target_type_mock = mock.MagicMock(return_value="ecs")
        select_ecs_cluster_mock = mock.MagicMock(return_value="arn:aws:ecs:us-east-1:123456789012:cluster/cluster-1")
        select_ecs_service_mock = mock.MagicMock(return_value="arn:aws:ecs:us-east-1:123456789012:service/service-1")
        select_ecs_task_mock = mock.MagicMock(
            side_effect=[
                "arn:aws:ecs:us-east-1:123456789012:task/cluster-1/task-1",
                "arn:aws:ecs:us-east-1:123456789012:task/cluster-1/task-2",
            ]
        )
        select_ecs_container_mock = mock.MagicMock(side_effect=[None, "runtime-id-2"])

        def prompt_dispatcher(title: str, *_args: object, **_kwargs: object) -> object:
            if "Target Type" in title:
                return target_type_mock()
            return None

        monkeypatch.setattr("aws_annoying.cli.session_manager.start._prompt_select", prompt_dispatcher)
        monkeypatch.setattr("aws_annoying.cli.session_manager.start._select_ecs_cluster", select_ecs_cluster_mock)
        monkeypatch.setattr("aws_annoying.cli.session_manager.start._select_ecs_service", select_ecs_service_mock)
        monkeypatch.setattr("aws_annoying.cli.session_manager.start._select_ecs_task", select_ecs_task_mock)
        monkeypatch.setattr(
            "aws_annoying.cli.session_manager.start._select_ecs_container_in_task",
            select_ecs_container_mock,
        )

        result = _handle_interactive_start()
        assert result == "ecs:cluster-1_task-2_runtime-id-2"


class Test_prompt_select:
    def test_select_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_q = mock.MagicMock()
        mock_q.ask.return_value = "val1"
        monkeypatch.setattr("questionary.select", mock.MagicMock(return_value=mock_q))

        result = _prompt_select("Select Item:", [("val1", "Label 1"), ("val2", "Label 2")])
        assert result == "val1"

    def test_select_cancel_with_allow_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_q = mock.MagicMock()
        mock_q.ask.return_value = None
        monkeypatch.setattr("questionary.select", mock.MagicMock(return_value=mock_q))

        result = _prompt_select("Select Item:", [("val1", "Label 1")], allow_back=True)
        assert result is None

    def test_select_cancel_without_allow_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_q = mock.MagicMock()
        mock_q.ask.return_value = None
        monkeypatch.setattr("questionary.select", mock.MagicMock(return_value=mock_q))

        with pytest.raises(typer.Exit) as exc_info:
            _prompt_select("Select Item:", [("val1", "Label 1")], allow_back=False)
        assert exc_info.value.exit_code == 1

    def test_escape_key_binding(self, monkeypatch: pytest.MonkeyPatch) -> None:
        kb = KeyBindings()
        mock_q = mock.MagicMock()
        mock_q.application.key_bindings = kb
        mock_q.ask.return_value = None
        monkeypatch.setattr("questionary.select", mock.MagicMock(return_value=mock_q))

        _prompt_select("Select Item:", [("val1", "Label 1")], allow_back=True)
        # Verify escape binding was added
        escape_bindings = [b for b in kb.bindings if any(str(getattr(k, "value", k)) == "escape" for k in b.keys)]
        assert len(escape_bindings) == 1

        mock_event = mock.MagicMock()
        escape_bindings[0].call(mock_event)
        mock_event.app.exit.assert_called_once_with(result=None)


def test_get_cluster_name() -> None:
    assert _get_cluster_name("arn:aws:ecs:us-east-1:123456789012:cluster/prod-cluster") == "prod-cluster"
    assert _get_cluster_name("prod-cluster") == "prod-cluster"


def test_get_service_name() -> None:
    assert _get_service_name("arn:aws:ecs:us-east-1:123456789012:service/prod-cluster/web-service") == "web-service"
    assert _get_service_name("web-service") == "web-service"


def test_get_task_id() -> None:
    assert _get_task_id("arn:aws:ecs:us-east-1:123456789012:task/prod-cluster/1234567890abcdef0") == "1234567890abcdef0"
    assert _get_task_id("1234567890abcdef0") == "1234567890abcdef0"

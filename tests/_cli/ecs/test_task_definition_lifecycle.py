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


def test_basic() -> None:
    """The command should deregister the oldest task definitions."""
    # Arrange
    ecs = boto3.client("ecs")
    family = "my-task"
    num_task_defs = 25
    for i in range(1, num_task_defs + 1):
        ecs.register_task_definition(
            family=family,
            containerDefinitions=[
                {
                    "name": "my-container",
                    "image": f"my-image:{i}",
                    "cpu": 0,
                    "memory": 0,
                },
            ],
        )

    # Act
    keep_latest = 10
    result = runner.invoke(
        app,
        [
            "ecs",
            "task-definition-lifecycle",
            "--family",
            family,
            "--keep-latest",
            str(keep_latest),
        ],
    )

    # Assert
    assert result.exit_code == 0
    assert normalize_console_output(result.stdout) == snapshot("""\
⚠️ Deregistering 15 task definitions...
⚠️ Deregistered task definition 'my-task:1'
⚠️ Deregistered task definition 'my-task:2'
⚠️ Deregistered task definition 'my-task:3'
⚠️ Deregistered task definition 'my-task:4'
⚠️ Deregistered task definition 'my-task:5'
⚠️ Deregistered task definition 'my-task:6'
⚠️ Deregistered task definition 'my-task:7'
⚠️ Deregistered task definition 'my-task:8'
⚠️ Deregistered task definition 'my-task:9'
⚠️ Deregistered task definition 'my-task:10'
⚠️ Deregistered task definition 'my-task:11'
⚠️ Deregistered task definition 'my-task:12'
⚠️ Deregistered task definition 'my-task:13'
⚠️ Deregistered task definition 'my-task:14'
⚠️ Deregistered task definition 'my-task:15'\
""")

    active_task_definitions = ecs.list_task_definitions(familyPrefix=family, status="ACTIVE")
    assert active_task_definitions["taskDefinitionArns"] == [
        f"arn:aws:ecs:us-east-1:123456789012:task-definition/{family}:{i}" for i in range(16, 26)
    ]

    inactive_task_definitions = ecs.list_task_definitions(familyPrefix=family, status="INACTIVE")
    assert inactive_task_definitions["taskDefinitionArns"] == [
        f"arn:aws:ecs:us-east-1:123456789012:task-definition/{family}:{i}" for i in range(1, 16)
    ]


def test_delete() -> None:
    """The command should deregister the oldest task definitions."""
    # Arrange
    ecs = boto3.client("ecs")
    family = "my-task"
    num_task_defs = 25
    for i in range(1, num_task_defs + 1):
        ecs.register_task_definition(
            family=family,
            containerDefinitions=[
                {
                    "name": "my-container",
                    "image": f"my-image:{i}",
                    "cpu": 0,
                    "memory": 0,
                },
            ],
        )

    # Act
    keep_latest = 10
    result = runner.invoke(
        app,
        [
            "ecs",
            "task-definition-lifecycle",
            "--family",
            family,
            "--keep-latest",
            str(keep_latest),
            "--delete",
        ],
    )

    # Assert
    assert result.exit_code == 0
    assert normalize_console_output(result.stdout) == snapshot("""\
⚠️ Deregistering 15 task definitions...
⚠️ Deregistered task definition 'my-task:1'
⚠️ Deregistered task definition 'my-task:2'
⚠️ Deregistered task definition 'my-task:3'
⚠️ Deregistered task definition 'my-task:4'
⚠️ Deregistered task definition 'my-task:5'
⚠️ Deregistered task definition 'my-task:6'
⚠️ Deregistered task definition 'my-task:7'
⚠️ Deregistered task definition 'my-task:8'
⚠️ Deregistered task definition 'my-task:9'
⚠️ Deregistered task definition 'my-task:10'
⚠️ Deregistered task definition 'my-task:11'
⚠️ Deregistered task definition 'my-task:12'
⚠️ Deregistered task definition 'my-task:13'
⚠️ Deregistered task definition 'my-task:14'
⚠️ Deregistered task definition 'my-task:15'
⚠️ Deleting 15 task definitions in chunks of size 10...
⚠️ Deleted 10 task definitions in 0-th batch.
⚠️ Deleted 5 task definitions in 1-th batch.\
""")

    active_task_definitions = ecs.list_task_definitions(familyPrefix=family, status="ACTIVE")
    assert active_task_definitions["taskDefinitionArns"] == [
        f"arn:aws:ecs:us-east-1:123456789012:task-definition/{family}:{i}" for i in range(16, 26)
    ]

    inactive_task_definitions = ecs.list_task_definitions(familyPrefix=family, status="INACTIVE")
    assert inactive_task_definitions["taskDefinitionArns"] == []

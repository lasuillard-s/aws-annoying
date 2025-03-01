import boto3
from typer.testing import CliRunner

from aws_annoying.main import app

from ._helpers import normalize_console_output

runner = CliRunner()

# ?: Moto (v5.1.1) `ecs.list_task_definitions` does not handle `status` filter properly
# !:               + sorting also does not work (current behavior is ASC)


def test_ecs_task_definition_lifecycle() -> None:
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
            "ecs-task-definition-lifecycle",
            "--family",
            family,
            "--keep-latest",
            str(keep_latest),
        ],
    )

    # Assert
    assert result.exit_code == 0
    assert (
        normalize_console_output(result.stdout)
        == """
✅ Deregistered task definition 'my-task:1'
✅ Deregistered task definition 'my-task:2'
✅ Deregistered task definition 'my-task:3'
✅ Deregistered task definition 'my-task:4'
✅ Deregistered task definition 'my-task:5'
✅ Deregistered task definition 'my-task:6'
✅ Deregistered task definition 'my-task:7'
✅ Deregistered task definition 'my-task:8'
✅ Deregistered task definition 'my-task:9'
✅ Deregistered task definition 'my-task:10'
✅ Deregistered task definition 'my-task:11'
✅ Deregistered task definition 'my-task:12'
✅ Deregistered task definition 'my-task:13'
✅ Deregistered task definition 'my-task:14'
✅ Deregistered task definition 'my-task:15'
""".strip()
    )

    task_definitions = [
        ecs.describe_task_definition(taskDefinition=f"{family}:{i}")["taskDefinition"]
        for i in range(1, num_task_defs + 1)
    ]
    assert [td["revision"] for td in task_definitions if td["status"] == "INACTIVE"] == list(
        range(1, num_task_defs - keep_latest + 1),  # 1..15
    )
    assert [td["revision"] for td in task_definitions if td["status"] == "ACTIVE"] == list(
        range(num_task_defs - keep_latest + 1, num_task_defs + 1),  # 16..25
    )


def test_ecs_task_definition_lifecycle_dry_run() -> None:
    """If `--dry-run` option given, the command should not perform any changes."""
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
            "ecs-task-definition-lifecycle",
            "--family",
            family,
            "--keep-latest",
            str(keep_latest),
            "--dry-run",
        ],
    )

    # Assert
    assert result.exit_code == 0
    assert normalize_console_output(result.stdout) == (
        """
✅ Deregistered task definition 'my-task:1'
✅ Deregistered task definition 'my-task:2'
✅ Deregistered task definition 'my-task:3'
✅ Deregistered task definition 'my-task:4'
✅ Deregistered task definition 'my-task:5'
✅ Deregistered task definition 'my-task:6'
✅ Deregistered task definition 'my-task:7'
✅ Deregistered task definition 'my-task:8'
✅ Deregistered task definition 'my-task:9'
✅ Deregistered task definition 'my-task:10'
✅ Deregistered task definition 'my-task:11'
✅ Deregistered task definition 'my-task:12'
✅ Deregistered task definition 'my-task:13'
✅ Deregistered task definition 'my-task:14'
✅ Deregistered task definition 'my-task:15'
""".strip()
    )

    task_definitions = [
        ecs.describe_task_definition(taskDefinition=f"{family}:{i}")["taskDefinition"]
        for i in range(1, num_task_defs + 1)
    ]
    assert [td["revision"] for td in task_definitions if td["status"] == "INACTIVE"] == []
    assert len([td["revision"] for td in task_definitions if td["status"] == "ACTIVE"]) == num_task_defs

import boto3
from typer.testing import CliRunner

from aws_annoying.main import app

runner = CliRunner()


def test_nothing() -> None:
    """If nothing is provided, the command should do nothing."""
    # Arrange
    # ...

    # Act
    result = runner.invoke(
        app,
        [
            "load-variables",
        ],
    )

    # Assert
    assert result.exit_code == 0
    assert result.stdout == ""


def test_ecs_task_definition_lifecycle() -> None:
    """If nothing is provided, the command should do nothing."""
    # Arrange
    ecs = boto3.client("ecs")
    family = "my-task"
    for i in range(25):
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
    result = runner.invoke(
        app,
        [
            "ecs-task-definition-lifecycle",
            "--family",
            family,
            "--keep-latest",
            "10",
        ],
    )

    # Assert
    assert result.exit_code == 0
    assert result.stdout != ""

    # TODO(lasuillard): Moto does not support filtering by status yet
    # assert len(ecs.list_task_definitions(familyPrefix=family, status="INACTIVE")["taskDefinitionArns"]) == 15  # noqa: ERA001, E501
    # assert len(ecs.list_task_definitions(familyPrefix=family, status="ACTIVE")["taskDefinitionArns"]) == 10  # noqa: ERA001, E501

import enum
import logging
import os
from collections.abc import Sequence
from typing import TYPE_CHECKING, TypeVar

import boto3
import questionary
import typer
from prompt_toolkit.key_binding import KeyBindings
from questionary import Choice

from aws_annoying.ec2 import get_instance_id_by_name
from aws_annoying.session_manager import SessionManager

from ._app import session_manager_app

if TYPE_CHECKING:
    from mypy_boto3_ec2 import EC2Client
    from mypy_boto3_ecs import ECSClient
    from prompt_toolkit.key_binding import KeyPressEvent

logger = logging.getLogger(__name__)

T = TypeVar("T")


@session_manager_app.command()
def start(
    *,
    target: str | None = typer.Option(
        None,
        help="The name or ID of the EC2 instance, or ECS target to connect to. If omitted, prompts interactively.",
    ),
    reason: str = typer.Option(
        "",
        help="The reason for starting the session.",
    ),
) -> None:
    """Start new session to your instance or ECS container.

    You can use your EC2 instance identified by its name or ID, or an ECS target
    formatted as `ecs:<cluster-name>_<task-id>_<container-runtime-id>`.

    Required IAM Permissions:

    - For EC2 instances:
      - `ec2:DescribeInstances`
      - `ssm:StartSession`
    - For ECS Exec (containers):
      - `ecs:DescribeTasks`
      - `ecs:ListClusters`
      - `ecs:ListServices`
      - `ecs:ListTasks`
      - `ssm:StartSession` (uses the SSM Session Manager instead of ECS Exec directly)
    """
    session_manager = SessionManager()

    if target is None:
        target = _handle_interactive_start()

    if not _is_ecs_target(target):
        # EC2 logic: Resolve the instance name or ID
        instance_id = get_instance_id_by_name(target)
        if instance_id:
            logger.info("Instance ID resolved: [bold]%s[/bold]", instance_id)
            target = instance_id
        else:
            logger.info("Instance with name '%s' not found.", target)
            raise typer.Exit(1)

    # Start the session, replacing the current process
    logger.info(
        "Starting session to target [bold]%s[/bold] with reason: [italic]%r[/italic].",
        target,
        reason,
    )
    command = session_manager.build_command(
        target=target,
        document_name="SSM-SessionManagerRunShell",
        parameters={},
        reason=reason,
    )
    os.execvp(command[0], command)  # noqa: S606


class _Step(enum.IntEnum):
    TARGET_TYPE = 0
    EC2_INSTANCE = 1
    ECS_CLUSTER = 2
    ECS_SERVICE = 3
    ECS_TASK = 4
    ECS_CONTAINER = 5


# NOTE: Each selection functions paginate ALL the results. For large accounts, this could be a performance issue.
#       In the future, we may want to implement a more efficient way to handle large result sets
def _handle_interactive_start() -> str:
    """Handle interactive target selection.

    Returns:
        The selected EC2 instance ID or ECS target string.
    """
    session = boto3.session.Session()
    ec2 = session.client("ec2")
    ecs = session.client("ecs")

    step = _Step.TARGET_TYPE
    cluster_arn: str | None = None
    service_arn: str | None = None
    task_arn: str | None = None

    while True:
        match step:
            case _Step.TARGET_TYPE:
                target_type = _prompt_select(
                    "Select Target Type:",
                    choices=[
                        ("ec2", "EC2 Instance"),
                        ("ecs", "ECS Exec (Container)"),
                    ],
                    use_search_filter=False,
                )
                step = _Step.EC2_INSTANCE if target_type == "ec2" else _Step.ECS_CLUSTER
            case _Step.EC2_INSTANCE:
                instance_id = _select_ec2_instance(ec2)
                if instance_id:
                    return instance_id

                step = _Step.TARGET_TYPE
            case _Step.ECS_CLUSTER:
                cluster_arn = _select_ecs_cluster(ecs)
                step = _Step.ECS_SERVICE if cluster_arn else _Step.TARGET_TYPE
            case _Step.ECS_SERVICE:
                service_arn = _select_ecs_service(ecs, cluster_arn or "")
                step = _Step.ECS_TASK if service_arn else _Step.ECS_CLUSTER
            case _Step.ECS_TASK:
                task_arn = _select_ecs_task(ecs, cluster_arn or "", service_arn or "")
                step = _Step.ECS_CONTAINER if task_arn else _Step.ECS_SERVICE
            case _Step.ECS_CONTAINER:
                runtime_id = _select_ecs_container_in_task(ecs, cluster_arn or "", task_arn or "")
                if not runtime_id:
                    step = _Step.ECS_TASK
                    continue

                cluster_name = _get_cluster_name(cluster_arn or "")
                task_id = _get_task_id(task_arn or "")
                return _build_ecs_target(cluster_name, task_id, runtime_id)


def _select_ec2_instance(ec2: "EC2Client") -> str | None:
    """Interactively select an EC2 instance.

    Args:
        ec2: Boto3 EC2 client to use.

    Returns:
        The selected EC2 instance ID, or None if cancelled.
    """
    instances: list[tuple[str, str]] = []
    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running"]}]):
        for res in page.get("Reservations", []):
            for instance in res.get("Instances", []):
                instance_id = instance["InstanceId"]
                name = instance_id
                for tag in instance.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break

                instances.append((instance_id, f"{name} ({instance_id})"))

    if not instances:
        logger.error("No running EC2 instances found.")
        return None

    logger.debug("Found %d running EC2 instances.", len(instances))
    return _prompt_select("Select EC2 Instance:", instances, allow_back=True)


def _select_ecs_cluster(ecs: "ECSClient") -> str | None:
    """Interactively select an ECS cluster.

    Args:
        ecs: Boto3 ECS client to use.

    Returns:
        The selected ECS cluster ARN, or None if cancelled.
    """
    cluster_arns: list[str] = []
    cluster_paginator = ecs.get_paginator("list_clusters")
    for c_page in cluster_paginator.paginate():
        cluster_arns.extend(c_page.get("clusterArns", []))

    if not cluster_arns:
        logger.error("No ECS clusters found.")
        return None

    logger.debug("Found %d ECS clusters.", len(cluster_arns))
    cluster_choices = [(arn, _get_cluster_name(arn)) for arn in cluster_arns]
    return _prompt_select("Select ECS Cluster:", cluster_choices, allow_back=True)


def _select_ecs_service(ecs: "ECSClient", cluster_arn: str) -> str | None:
    """Interactively select an ECS service.

    Args:
        ecs: Boto3 ECS client to use.
        cluster_arn: The ECS cluster ARN.

    Returns:
        The selected ECS service ARN, or None if cancelled.
    """
    cluster_name = _get_cluster_name(cluster_arn)

    service_arns: list[str] = []
    service_paginator = ecs.get_paginator("list_services")
    for page in service_paginator.paginate(cluster=cluster_arn):
        service_arns.extend(page.get("serviceArns", []))

    if not service_arns:
        logger.warning("No ECS services found in cluster '%s'.", cluster_name)
        return None

    logger.debug("Found %d ECS services in cluster '%s'.", len(service_arns), cluster_name)
    service_choices = [(arn, _get_service_name(arn)) for arn in service_arns]
    return _prompt_select("Select ECS Service:", service_choices, allow_back=True)


def _select_ecs_task(ecs: "ECSClient", cluster_arn: str, service_arn: str) -> str | None:
    """Interactively select an ECS task.

    Args:
        ecs: Boto3 ECS client to use.
        cluster_arn: The ECS cluster ARN.
        service_arn: The ECS service ARN.

    Returns:
        The selected ECS task ARN, or None if cancelled.
    """
    service_name = _get_service_name(service_arn)

    tasks: list[str] = []
    task_paginator = ecs.get_paginator("list_tasks")
    for page in task_paginator.paginate(cluster=cluster_arn, serviceName=service_name):
        tasks.extend(page.get("taskArns", []))

    if not tasks:
        logger.warning("No running ECS tasks found for service '%s'.", service_name)
        return None

    logger.debug("Found %d running ECS tasks for service '%s'.", len(tasks), service_name)
    task_choices = [(arn, _get_task_id(arn)) for arn in tasks]
    return _prompt_select("Select ECS Task:", task_choices, allow_back=True)


def _select_ecs_container_in_task(ecs: "ECSClient", cluster_arn: str, task_arn: str) -> str | None:
    """Interactively select an ECS container in a task.

    Args:
        ecs: Boto3 ECS client to use.
        cluster_arn: The ECS cluster ARN.
        task_arn: The ECS task ARN.

    Returns:
        The container runtime ID, or None if cancelled.
    """
    task_id = _get_task_id(task_arn)
    task_details = ecs.describe_tasks(cluster=cluster_arn, tasks=[task_arn])
    tasks = task_details.get("tasks", [])
    if not tasks:
        logger.warning("ECS task '%s' not found.", task_id)
        return None

    containers = tasks[0].get("containers", [])
    if not containers:
        logger.warning("No containers found in task '%s'.", task_id)
        return None

    container_choices: list[tuple[str, str]] = []
    name_to_container_runtime_id: dict[str, str] = {}
    for container in containers:
        name = str(container["name"])
        runtime_id = str(container.get("runtimeId") or name)
        container_choices.append((name, name))
        name_to_container_runtime_id[name] = runtime_id

    selected_name = _prompt_select("Select ECS Container:", container_choices, allow_back=True)
    if not selected_name:
        return None

    return name_to_container_runtime_id.get(selected_name, selected_name)


def _prompt_select(
    title: str,
    choices: Sequence[tuple["T", str]],
    *,
    allow_back: bool = False,
    use_search_filter: bool = True,
) -> T | None:
    """Prompt user to select one of the choices interactively.

    Args:
        title: The title of the prompt.
        choices: A sequence of tuples (value, label).
        allow_back: Whether going back is allowed.
        use_search_filter: Whether to enable typing to filter options.

    Returns:
        The selected value, or None if the prompt was cancelled/backed out.
    """
    question_choices = [Choice(title=label, value=value) for value, label in choices]
    q = questionary.select(
        title,
        choices=question_choices,
        use_jk_keys=not use_search_filter,
        use_search_filter=use_search_filter,
    )

    # Add a key binding for "Escape" to exit the prompt (go back)
    if isinstance(q.application.key_bindings, KeyBindings):

        @q.application.key_bindings.add("escape", eager=True)
        def _on_escape(event: "KeyPressEvent") -> None:
            event.app.exit(result=None)

    result: T | None = q.ask()
    if result is None and not allow_back:
        raise typer.Exit(1)

    return result


def _get_cluster_name(cluster_arn: str) -> str:
    """Extract cluster name from ECS cluster ARN."""
    return cluster_arn.rsplit("/", maxsplit=1)[-1]


def _get_service_name(service_arn: str) -> str:
    """Extract service name from ECS service ARN."""
    return service_arn.rsplit("/", maxsplit=1)[-1]


def _get_task_id(task_arn: str) -> str:
    """Extract task ID from ECS task ARN."""
    return task_arn.rsplit("/", maxsplit=1)[-1]


def _is_ecs_target(target: str) -> bool:
    """Check if the given string is an ECS connection string (ecs:*_*_*)."""
    if not target.startswith("ecs:"):
        return False

    parts = target[4:].split("_")
    return len(parts) == 3 and all(parts)  # noqa: PLR2004


def _build_ecs_target(cluster: str, task: str, container: str) -> str:
    """Build an ECS connection string (ecs:<cluster>_<task>_<container>)."""
    return f"ecs:{cluster}_{task}_{container}"

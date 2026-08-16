from __future__ import annotations

import boto3
import typer

from aws_annoying.cli.ui import prompt_select


def select_ec2_instance(session: boto3.session.Session | None = None) -> str:
    """Interactively select an EC2 instance.

    Args:
        session: Boto3 session to use.

    Returns:
        The selected EC2 instance ID.
    """
    session = session or boto3.session.Session()
    ec2 = session.client("ec2")
    instances: list[tuple[str, str]] = []

    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running"]}]):
        for res in page.get("Reservations", []):
            for inst in res.get("Instances", []):
                iid = inst["InstanceId"]
                name = iid
                for tag in inst.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break
                instances.append((iid, f"{name} ({iid})"))

    if not instances:
        typer.secho("No running EC2 instances found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    return prompt_select("EC2 Instances", instances)


def select_ecs_container(session: boto3.session.Session | None = None) -> tuple[str, str, str]:
    """Interactively select an ECS container.

    Args:
        session: Boto3 session to use.

    Returns:
        A tuple of (cluster_name, task_arn, container_name).
    """
    session = session or boto3.session.Session()
    ecs = session.client("ecs")

    # 1. Cluster
    clusters: list[str] = []
    cluster_paginator = ecs.get_paginator("list_clusters")
    for c_page in cluster_paginator.paginate():
        clusters.extend(c_page.get("clusterArns", []))
    if not clusters:
        typer.secho("No ECS clusters found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    cluster_choices = [(c, c.rsplit("/", maxsplit=1)[-1]) for c in clusters]
    cluster = prompt_select("ECS Cluster", cluster_choices)

    # 2. Service
    services: list[str] = []
    service_paginator = ecs.get_paginator("list_services")
    for s_page in service_paginator.paginate(cluster=cluster):
        services.extend(s_page.get("serviceArns", []))

    if not services:
        typer.secho("No ECS services found in cluster.", fg=typer.colors.RED)
        raise typer.Exit(1)

    service_choices = [(s, s.rsplit("/", maxsplit=1)[-1]) for s in services]
    service = prompt_select("ECS Service", service_choices)

    # 3. Task
    tasks: list[str] = []
    task_paginator = ecs.get_paginator("list_tasks")
    for t_page in task_paginator.paginate(cluster=cluster, serviceName=service):
        tasks.extend(t_page.get("taskArns", []))

    if not tasks:
        typer.secho("No running ECS tasks found for service.", fg=typer.colors.RED)
        raise typer.Exit(1)

    task_choices = [(t, t.rsplit("/", maxsplit=1)[-1]) for t in tasks]
    task = prompt_select("ECS Task", task_choices)

    # 4. Container
    task_details = ecs.describe_tasks(cluster=cluster, tasks=[task])
    containers = task_details["tasks"][0].get("containers", [])
    if not containers:
        typer.secho("No containers found in task.", fg=typer.colors.RED)
        raise typer.Exit(1)

    container_choices = [(c["name"], c["name"]) for c in containers]
    container = prompt_select("ECS Container", container_choices)

    return cluster, task, container

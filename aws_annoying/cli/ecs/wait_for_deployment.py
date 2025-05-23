from __future__ import annotations

import signal
from time import sleep
from typing import TYPE_CHECKING, Optional

import boto3
import typer
from rich import print  # noqa: A004

from ._app import ecs_app

if TYPE_CHECKING:
    from types import FrameType
    from typing import Any


@ecs_app.command()
def wait_for_deployment(
    *,
    cluster: str = typer.Option(
        ...,
        help="The name of the ECS cluster.",
        show_default=False,
    ),
    service: str = typer.Option(
        ...,
        help="The name of the ECS service.",
        show_default=False,
    ),
    task_definition: Optional[str] = typer.Option(
        None,
        help="The task definition for the service expected after deployment. If not provided, it will not be checked.",
        show_default=False,
    ),
    polling_interval: int = typer.Option(
        5,
        help="The interval between polling attempts, in seconds.",
    ),
    timeout: int = typer.Option(
        600,
        help="The maximum time to wait for the deployment to complete, in seconds.",
    ),
) -> None:
    """Wait for ECS deployment to complete."""
    ecs = boto3.client("ecs")

    # Find current deployment for the service
    running_deployments = ecs.list_service_deployments(
        cluster=cluster,
        service=service,
        status=["PENDING", "IN_PROGRESS"],
    )["serviceDeployments"]
    if not running_deployments:
        print(f"❗ No running deployments found for service {service}. Exiting.")
        raise typer.Exit(0)

    latest_deployment_arn = running_deployments[0]["serviceDeploymentArn"]

    # Polling for the deployment to finish (successfully or unsuccessfully)
    print(f"💬 Start checking for deployment [bold]{latest_deployment_arn}[/bold] to finish.")
    print(f"💬 It will check the deployment every {polling_interval} seconds, with {timeout} seconds of timeout.")

    def handler(signum: int, frame: FrameType | None) -> Any:  # noqa: ARG001
        msg = "Timeout reached"
        raise TimeoutError(msg)

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)
    try:
        i = 0
        while True:
            i += 1
            latest_deployment = ecs.describe_service_deployments(serviceDeploymentArns=[latest_deployment_arn])[
                "serviceDeployments"
            ][0]
            status = latest_deployment["status"]
            if status == "SUCCESSFUL":
                print(f"✅ Deployment succeeded with status [bold green]{status}[/bold green]")
                break

            if status in ("PENDING", "IN_PROGRESS"):
                print(f"💬 Deployment in progress; [bold grey53]{status}[/bold grey53] ({i}-th attempt)")
            else:
                print(f"❌ Deployment failed with status [bold red]{status}[/bold red]")
                raise typer.Exit(1)

            sleep(polling_interval)
    except TimeoutError:
        print(f"⌛️ Deployment check timed out after {timeout} seconds.")
    finally:
        signal.alarm(0)

    # Check if the task definition is the expected one
    if task_definition:
        service_detail = ecs.describe_services(cluster=cluster, services=[service])["services"][0]
        if service_detail["taskDefinition"] == task_definition:
            print(f"✅ The service task definition is the expected one: [bold green]{task_definition}[/bold green]")
        else:
            print(
                f"❗ The service task definition is not the expected one: [bold red]{service_detail['taskDefinition']}[/bold red]",  # noqa: E501
            )
            raise typer.Exit(1)

    # TODO(lasuillard): The service can be in a state where the deployment is still in progress (draining)
    #                   More advanced logic can be added to check the status of the service


class TimeoutError(Exception):  # noqa: A001
    """Deployment check timed out."""

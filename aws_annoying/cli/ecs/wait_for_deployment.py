from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import typer

from aws_annoying.ecs import (
    DeploymentFailedError,
    ECSServiceRef,
    ServiceTaskDefinitionAssertionError,
    check_service_task_definition,
    wait_for_deployment_complete,
    wait_for_deployment_start,
    wait_for_service_stability,
)
from aws_annoying.utils.timeout import OperationTimeoutError, Timeout

from ._app import ecs_app

logger = logging.getLogger(__name__)


@ecs_app.command()
def wait_for_deployment(  # noqa: PLR0913
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
    expected_task_definition: Optional[str] = typer.Option(
        None,
        help=(
            "The service's task definition expected after deployment."
            " If provided, it will be used to assert the service's task definition after deployment finished or timed out."  # noqa: E501
        ),
        show_default=False,
    ),
    polling_interval: int = typer.Option(
        5,
        help="The interval between any polling attempts, in seconds.",
        min=1,
    ),
    timeout_seconds: Optional[int] = typer.Option(
        None,
        help=(
            "The maximum time to wait for the deployment to complete, in seconds."
            " If not provided, it will wait indefinitely."
        ),
        min=1,
    ),
    wait_for_start: bool = typer.Option(
        True,  # noqa: FBT003
        help=(
            "Whether to wait for the deployment to start."
            " Because there could be no deployment right after the deploy,"
            " this option will wait for a new deployment to start if no running deployment is found."
        ),
    ),
    wait_for_stability: bool = typer.Option(
        False,  # noqa: FBT003
        help="Whether to wait for the service to be stable after the deployment.",
    ),
) -> None:
    """Wait for ECS deployment to complete."""
    start = datetime.now(tz=timezone.utc)
    try:
        with Timeout(timeout_seconds):
            _wait_for_deployment(
                ECSServiceRef(cluster=cluster, service=service),
                wait_for_start=wait_for_start,
                polling_interval=polling_interval,
                wait_for_stability=wait_for_stability,
                expected_task_definition=expected_task_definition,
            )
    except OperationTimeoutError:
        logger.error(  # noqa: TRY400
            "Timeout reached after %s seconds. The deployment may not have finished.",
            timeout_seconds,
        )
        raise typer.Exit(1) from None
    except DeploymentFailedError as err:
        elapsed = datetime.now(tz=timezone.utc) - start
        logger.error(  # noqa: TRY400
            "Deployment failed in [bold]%.2f[/bold] seconds with error: %s",
            elapsed.total_seconds(),
            err,
        )
        raise typer.Exit(1) from None
    else:
        elapsed = datetime.now(tz=timezone.utc) - start
        logger.info(
            "Deployment completed in [bold]%.2f[/bold] seconds.",
            elapsed.total_seconds(),
        )


def _wait_for_deployment(
    service_ref: ECSServiceRef,
    *,
    wait_for_start: bool,
    polling_interval: int = 5,
    wait_for_stability: bool,
    expected_task_definition: str | None = None,
) -> None:
    # Find current deployment for the service
    logger.info(
        "Looking up running deployment for service %s",
        service_ref.service,
    )
    latest_deployment_arn = wait_for_deployment_start(
        service_ref,
        wait_for_start=wait_for_start,
        polling_interval=polling_interval,
    )

    # Polling for the deployment to finish (successfully or unsuccessfully)
    logger.info(
        "Start waiting for deployment %s to finish.",
        latest_deployment_arn,
    )
    ok, status = wait_for_deployment_complete(latest_deployment_arn, polling_interval=polling_interval)
    if ok:
        logger.info(
            "Deployment succeeded with status %s",
            status,
        )
    else:
        msg = f"Deployment failed with status: {status}"
        raise DeploymentFailedError(msg)

    # Wait for the service to be stable
    if wait_for_stability:
        logger.info(
            "Start waiting for service %s to be stable.",
            service_ref.service,
        )
        wait_for_service_stability(service_ref, polling_interval=polling_interval)

    # Check if the service task definition matches the expected one
    if expected_task_definition:
        logger.info(
            "Checking if the service task definition is the expected one: %s",
            expected_task_definition,
        )
        ok, actual = check_service_task_definition(service_ref, expect=expected_task_definition)
        if not ok:
            msg = f"The service task definition is not the expected one; got: {actual!r}"
            raise ServiceTaskDefinitionAssertionError(msg)

        logger.info("The service task definition matches the expected one.")

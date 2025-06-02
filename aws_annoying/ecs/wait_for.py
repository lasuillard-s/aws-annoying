from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import sleep
from typing import TYPE_CHECKING

import boto3
import botocore.exceptions

from .errors import NoRunningDeploymentError

if TYPE_CHECKING:
    from .common import ECSServiceRef

logger = logging.getLogger(__name__)


def wait_for_deployment_start(
    service_ref: ECSServiceRef,
    *,
    session: boto3.session.Session | None = None,
    wait_for_start: bool,
    polling_interval: int = 5,
    max_attempts: int | None = None,
) -> str:
    """Wait for the ECS deployment to start.

    Args:
        service_ref: The ECS service reference containing the cluster and service names.
        session: The boto3 session to use for the ECS client.
        wait_for_start: Whether to wait for the deployment to start.
        polling_interval: The interval between any polling attempts, in seconds.
        max_attempts: The maximum number of attempts to wait for the deployment to start.

    Raises:
        NoRunningDeploymentError: If no running deployments are found and `wait_for_start` is False.

    Returns:
        The ARN of the latest deployment for the service.
    """
    session = session or boto3.session.Session()
    ecs = session.client("ecs")

    if wait_for_start:
        logger.warning("`wait_for_start` is set, will wait for a new deployment to start.")

    attempts = 0
    while True:  # do-while
        # Do
        running_deployments = ecs.list_service_deployments(
            cluster=service_ref.cluster,
            service=service_ref.service,
            status=["PENDING", "IN_PROGRESS"],
        )["serviceDeployments"]

        # While
        if running_deployments:
            logger.debug("Found %d running deployments for service. Exiting loop.", len(running_deployments))
            break

        if not wait_for_start:
            logger.debug("`wait_for_start` is off, no need to wait for a new deployment to start.")
            break

        if max_attempts and attempts >= max_attempts:
            logger.debug("Max attempts exceeded while waiting for a new deployment to start.")
            break

        logger.debug(
            "(%d-th attempt) No running deployments found for service. Start waiting for a new deployment.",
            attempts + 1,
        )

        sleep(polling_interval)
        attempts += 1

    if not running_deployments:
        msg = "No running deployments found for service."
        raise NoRunningDeploymentError(msg)

    latest_deployment = max(
        running_deployments,
        key=lambda dep: dep.get(
            "startedAt",
            datetime.min.replace(tzinfo=timezone.utc),
        ),
    )
    if len(running_deployments) > 1:
        logger.warning(
            "%d running deployments found for service. Using most recently started deployment: %s",
            len(running_deployments),
            latest_deployment["serviceDeploymentArn"],
        )

    return latest_deployment["serviceDeploymentArn"]


def wait_for_deployment_complete(
    deployment_arn: str,
    *,
    session: boto3.session.Session | None = None,
    polling_interval: int = 5,
    max_attempts: int | None = None,
) -> tuple[bool, str]:
    """Wait for the ECS deployment to complete.

    Args:
        deployment_arn: The ARN of the deployment to wait for.
        session: The boto3 session to use for the ECS client.
        polling_interval: The interval between any polling attempts, in seconds.
        max_attempts: The maximum number of attempts to wait for the deployment to complete.

    Returns:
        A tuple containing a boolean indicating whether the deployment succeeded and the status of the deployment.
    """
    session = session or boto3.session.Session()
    ecs = session.client("ecs")

    attempts = 0
    while (max_attempts is None) or (attempts <= max_attempts):
        latest_deployment = ecs.describe_service_deployments(serviceDeploymentArns=[deployment_arn])[
            "serviceDeployments"
        ][0]
        status = latest_deployment["status"]
        if status == "SUCCESSFUL":
            return (True, status)

        if status in ("PENDING", "IN_PROGRESS"):
            logger.debug(
                "(%d-th attempt) Deployment in progress... (%s)",
                attempts + 1,
                status,
            )
        else:
            break

        sleep(polling_interval)
        attempts += 1

    return (False, status)


def wait_for_service_stability(
    service_ref: ECSServiceRef,
    *,
    session: boto3.session.Session | None = None,
    polling_interval: int = 5,
    max_attempts: int | None = None,
) -> bool:
    """Wait for the ECS service to be stable.

    Args:
        service_ref: The ECS service reference containing the cluster and service names.
        session: The boto3 session to use for the ECS client.
        polling_interval: The interval between any polling attempts, in seconds.
        max_attempts: The maximum number of attempts to wait for the service to be stable.

    Returns:
        A boolean indicating whether the service is stable.
    """
    session = session or boto3.session.Session()
    ecs = session.client("ecs")

    # TODO(lasuillard): Likely to be a problem in some cases: https://github.com/boto/botocore/issues/3314
    stability_waiter = ecs.get_waiter("services_stable")

    attempts = 0
    while (max_attempts is None) or (attempts <= max_attempts):
        logger.debug(
            "(%d-th attempt) Waiting for service %s to be stable...",
            attempts + 1,
            service_ref.service,
        )
        try:
            stability_waiter.wait(
                cluster=service_ref.cluster,
                services=[service_ref.service],
                WaiterConfig={"Delay": polling_interval, "MaxAttempts": 1},
            )
        except botocore.exceptions.WaiterError as err:
            if err.kwargs["reason"] != "Max attempts exceeded":
                raise
        else:
            return True

        sleep(polling_interval)
        attempts += 1

    return False

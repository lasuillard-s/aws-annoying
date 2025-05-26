from __future__ import annotations

import logging
from operator import itemgetter
from time import sleep
from typing import TYPE_CHECKING, Optional

import boto3
import botocore.exceptions
from pydantic import PositiveInt, validate_call

from .errors import DeploymentFailedError, NoRunningDeploymentError, ServiceTaskDefinitionAssertionError

if TYPE_CHECKING:
    from .common import ECSServiceRef

logger = logging.getLogger(__name__)


class ECSDeploymentWaiter:
    """ECS service deployment waiter."""

    def __init__(self, service_ref: ECSServiceRef, *, session: boto3.session.Session | None = None) -> None:
        """Initialize instance.

        Args:
            service_ref: Reference to the ECS service.
            session: Boto3 session to use for AWS operations.

        """
        self.service_ref = service_ref
        self.session = session or boto3.session.Session()

    @validate_call
    def wait(
        self,
        *,
        wait_for_start: bool,
        polling_interval: PositiveInt = 5,
        wait_for_stability: bool,
        expected_task_definition: Optional[str] = None,
    ) -> None:
        """Wait for the ECS deployment to complete.

        Args:
            wait_for_start: Whether to wait for the deployment to start.
            polling_interval: The interval between any polling attempts, in seconds.
            wait_for_stability: Whether to wait for the service to be stable after the deployment.
            expected_task_definition: The service's task definition expected after deployment.
        """
        # Find current deployment for the service
        logger.info(
            "Looking up running deployment for service %s",
            self.service_ref.service,
        )
        latest_deployment_arn = self.get_latest_deployment_arn(
            wait_for_start=wait_for_start,
            polling_interval=polling_interval,
        )

        # Polling for the deployment to finish (successfully or unsuccessfully)
        logger.info(
            "Start waiting for deployment %s to finish.",
            latest_deployment_arn,
        )
        ok, status = self.wait_for_deployment_complete(latest_deployment_arn, polling_interval=polling_interval)
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
            logger.debug(
                "Start waiting for service %s to be stable.",
                self.service_ref.service,
            )
            self.wait_for_service_stability(polling_interval=polling_interval)

        # Check if the service task definition matches the expected one
        if expected_task_definition:
            logger.info(
                "Checking if the service task definition is the expected one: %s",
                expected_task_definition,
            )
            ok, actual = self.check_service_task_definition_is(expect=expected_task_definition)
            if not ok:
                msg = f"The service task definition is not the expected one; got: {actual!r}"
                raise ServiceTaskDefinitionAssertionError(msg)

            logger.info("The service task definition matches the expected one.")

    @validate_call
    def get_latest_deployment_arn(
        self,
        *,
        wait_for_start: bool,
        polling_interval: PositiveInt,
        max_attempts: Optional[PositiveInt] = None,
    ) -> str:
        """Get the most recently started deployment ARN for the service.

        Args:
            wait_for_start: Whether to wait for the deployment to start.
            polling_interval: The interval between any polling attempts, in seconds.
            max_attempts: The maximum number of attempts to wait for the deployment to start.

        Raises:
            NoRunningDeploymentError: If no running deployments are found and `wait_for_start` is False.

        Returns:
            The ARN of the latest deployment for the service.
        """
        ecs = self.session.client("ecs")
        if wait_for_start:
            logger.warning("`wait_for_start` is set, will wait for a new deployment to start.")

        attempts = 0
        while True:  # do-while
            # Do
            running_deployments = ecs.list_service_deployments(
                cluster=self.service_ref.cluster,
                service=self.service_ref.service,
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

        latest_deployment = sorted(running_deployments, key=itemgetter("startedAt"))[-1]
        if len(running_deployments) > 1:
            logger.warning(
                "%d running deployments found for service. Using most recently started deployment: %s",
                len(running_deployments),
                latest_deployment["serviceDeploymentArn"],
            )

        return latest_deployment["serviceDeploymentArn"]

    @validate_call
    def wait_for_deployment_complete(
        self,
        deployment_arn: str,
        *,
        polling_interval: PositiveInt,
        max_attempts: Optional[PositiveInt] = None,
    ) -> tuple[bool, str]:
        """Wait for the ECS deployment to complete.

        Args:
            deployment_arn: The ARN of the deployment to wait for.
            polling_interval: The interval between any polling attempts, in seconds.
            max_attempts: The maximum number of attempts to wait for the deployment to complete.

        Returns:
            A tuple containing a boolean indicating whether the deployment succeeded and the status of the deployment.
        """
        ecs = self.session.client("ecs")

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

    @validate_call
    def wait_for_service_stability(
        self,
        *,
        polling_interval: PositiveInt,
        max_attempts: Optional[PositiveInt] = None,
    ) -> bool:
        """Wait for the ECS service to be stable.

        Args:
            polling_interval: The interval between any polling attempts, in seconds.
            max_attempts: The maximum number of attempts to wait for the service to be stable.

        Returns:
            A boolean indicating whether the service is stable.
        """
        ecs = self.session.client("ecs")

        # TODO(lasuillard): Likely to be a problem in some cases: https://github.com/boto/botocore/issues/3314
        stability_waiter = ecs.get_waiter("services_stable")

        attempts = 0
        while (max_attempts is None) or (attempts <= max_attempts):
            logger.debug(
                "(%d-th attempt) Waiting for service %s to be stable...",
                attempts + 1,
                self.service_ref.service,
            )
            try:
                stability_waiter.wait(
                    cluster=self.service_ref.cluster,
                    services=[self.service_ref.service],
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

    @validate_call
    def check_service_task_definition_is(self, expect: str) -> tuple[bool, str]:
        """Check the service's current task definition matches the expected one.

        Args:
            expect: The ARN of expected task definition.

        Returns:
            A tuple containing a boolean indicating whether the task definition matches the expected one
            and the current task definition ARN.
        """
        ecs = self.session.client("ecs")

        service_detail = ecs.describe_services(cluster=self.service_ref.cluster, services=[self.service_ref.service])[
            "services"
        ][0]
        current_task_definition_arn = service_detail["taskDefinition"]
        if current_task_definition_arn != expect:
            return (False, current_task_definition_arn)

        return (True, current_task_definition_arn)

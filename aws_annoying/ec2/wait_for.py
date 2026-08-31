import logging
import time
from typing import Any

import botocore.client
import botocore.exceptions
from mypy_boto3_ssm import SSMClient

from .common import is_valid_instance_id
from .errors import InstanceNotReadyError, InvalidInstanceIdError

logger = logging.getLogger(__name__)


class InstanceReadinessWaiter:
    """Waiter for checking if an EC2 instance is ready via SSM commands."""

    transient_error_codes: frozenset[str] = frozenset(
        {
            "InvalidInstanceId",
            "InvocationDoesNotExist",
        }
    )

    def __init__(
        self,
        document_name: str,
        parameters: dict[str, Any],
        *,
        client: SSMClient,
        wait_duration: float = 5.0,
    ) -> None:
        """Initialize the waiter.

        Args:
            document_name: The SSM document name to execute.
            parameters: The parameters for the SSM document.
            client: The boto3 SSM client to use.
            wait_duration: Delay in seconds to wait before checking the command invocation result.
        """
        self.document_name = document_name
        self.parameters = parameters
        self.client = client
        self.wait_duration = wait_duration

    def wait_for_ready(self, instance_id: str, max_attempts: int = 10, delay: float = 30.0) -> bool:
        """Wait for an EC2 instance to be ready using the SSM health check.

        Args:
            instance_id: The ID of the EC2 instance.
            max_attempts: Maximum number of attempts to check readiness.
            delay: Delay in seconds between attempts.

        Returns:
            True if the instance became ready.

        Raises:
            InvalidInstanceIdError: If instance_id format is invalid.
            InstanceNotReadyError: If instance is not ready after max_attempts.
        """
        if not is_valid_instance_id(instance_id):
            msg = f"Invalid EC2 instance ID: '{instance_id}'"
            raise InvalidInstanceIdError(msg)

        logger.info("Waiting for instance %s to be ready...", instance_id)
        for attempt in range(max_attempts):
            logger.info("Attempt %d/%d...", attempt + 1, max_attempts)
            if self.check_ready(instance_id):
                logger.info("Instance %s is ready.", instance_id)
                return True

            if attempt < max_attempts - 1:
                time.sleep(delay)

        logger.error("Maximum attempts reached. Instance %s is not ready.", instance_id)
        msg = f"Instance '{instance_id}' failed to become ready after {max_attempts} attempts."
        raise InstanceNotReadyError(msg)

    def check_ready(self, instance_id: str) -> bool:
        """Perform a single health check attempt.

        Args:
            instance_id: The ID of the EC2 instance to check.

        Returns:
            True if the command execution succeeded, False otherwise (or if transient error).
        """
        try:
            result = self.client.send_command(
                InstanceIds=[instance_id],
                DocumentName=self.document_name,
                Parameters=self.parameters,
            )
            command_id = result["Command"]["CommandId"]

            self.wait()

            invocation = self.client.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id,
            )
            return invocation.get("Status") == "Success" and invocation.get("ResponseCode") == 0
        except botocore.exceptions.ClientError as err:
            if self.is_transient_error(err):
                logger.debug("SSM command check transient error on instance %s: %s", instance_id, err)
                return False

            logger.debug("SSM command check failed with non-transient error on instance %s: %s", instance_id, err)
            raise

    def is_transient_error(self, err: botocore.exceptions.ClientError) -> bool:
        """Check if the given botocore ClientError is a transient SSM error.

        Args:
            err: The ClientError encountered.

        Returns:
            True if the error is considered transient, False otherwise.
        """
        error_code = err.response.get("Error", {}).get("Code", "")
        return error_code in self.transient_error_codes

    def wait(self) -> None:
        """Wait before fetching the command invocation result.

        Can be overridden in subclasses for custom sleep behaviors.
        """
        time.sleep(self.wait_duration)

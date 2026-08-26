from __future__ import annotations

import logging
import time
from typing import Any, Optional, Protocol

import boto3
import botocore.exceptions

from .common import is_valid_instance_id
from .errors import InstanceNotReadyError, InvalidInstanceIdError

logger = logging.getLogger(__name__)

# Set of SSM error codes that are considered transient and may resolve on retry.
_TRANSIENT_SSM_ERROR_CODES = frozenset(
    {
        "InvalidInstanceId",
        "InvocationDoesNotExist",
    }
)


class InstanceChecker(Protocol):
    """Protocol for EC2 instance readiness checker functions."""

    def __call__(
        self,
        instance_id: str,
        /,
        *,
        session: Optional[boto3.session.Session] = None,
    ) -> bool:
        """Check if an instance is ready."""


def wait_for_instance_ready(
    instance_id: str,
    *,
    checker: InstanceChecker,
    session: Optional[boto3.session.Session] = None,
    max_attempts: int = 10,
    delay: float = 30.0,
) -> bool:
    """Wait for an EC2 instance to be ready using a health check function.

    Args:
        instance_id: The ID of the EC2 instance.
        checker: The health check function to execute.
        session: Optional boto3 session to use.
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

    session = session or boto3.session.Session()

    logger.info("Waiting for instance %s to be ready...", instance_id)
    for attempt in range(max_attempts):
        logger.info("Attempt %d/%d...", attempt + 1, max_attempts)
        if checker(instance_id, session=session):
            logger.info("Instance %s is ready.", instance_id)
            return True

        if attempt < max_attempts - 1:
            time.sleep(delay)

    logger.error("Maximum attempts reached. Instance %s is not ready.", instance_id)
    msg = f"Instance '{instance_id}' failed to become ready after {max_attempts} attempts."
    raise InstanceNotReadyError(msg)


def make_ssm_checker(
    document_name: str,
    parameters: dict[str, Any],
) -> InstanceChecker:
    """Build a custom SSM document checker with optional parameters."""

    def _checker(instance_id: str, *, session: Optional[boto3.session.Session] = None) -> bool:
        session = session or boto3.session.Session()
        ssm = session.client("ssm")
        try:
            result = ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName=document_name,
                Parameters=parameters,
            )
            command_id = result["Command"]["CommandId"]

            time.sleep(5)

            invocation = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id,
            )
            return invocation.get("Status") == "Success" and invocation.get("ResponseCode") == 0
        except botocore.exceptions.ClientError as err:
            error_code = err.response.get("Error", {}).get("Code", "")
            if error_code in _TRANSIENT_SSM_ERROR_CODES:
                logger.debug("SSM command check transient error on instance %s: %s", instance_id, err)
                return False

            logger.debug("SSM command check failed with non-transient error on instance %s: %s", instance_id, err)
            raise

    return _checker

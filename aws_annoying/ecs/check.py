from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import boto3

if TYPE_CHECKING:
    from .common import ECSServiceRef

logger = logging.getLogger(__name__)


def check_service_task_definition(
    service_ref: ECSServiceRef,
    *,
    session: boto3.session.Session | None = None,
    expect: str,
) -> tuple[bool, str]:
    """Check the service's current task definition matches the expected one.

    Args:
        service_ref: The ECS service reference containing the cluster and service names.
        session: The boto3 session to use for the ECS client.
        expect: The ARN of expected task definition.

    Returns:
        A tuple containing a boolean indicating whether the task definition matches the expected one
        and the current task definition ARN.
    """
    session = session or boto3.session.Session()
    ecs = session.client("ecs")

    service_detail = ecs.describe_services(cluster=service_ref.cluster, services=[service_ref.service])["services"][0]
    current_task_definition_arn = service_detail["taskDefinition"]
    if current_task_definition_arn != expect:
        return (False, current_task_definition_arn)

    return (True, current_task_definition_arn)

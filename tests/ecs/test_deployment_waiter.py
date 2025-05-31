from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest import mock

import boto3
import pytest
from botocore.stub import Stubber

from aws_annoying.ecs import ECSDeploymentWaiter
from aws_annoying.ecs.common import ECSServiceRef
from aws_annoying.ecs.errors import NoRunningDeploymentError

if TYPE_CHECKING:
    from mypy_boto3_ecs import ECSClient

pytestmark = [
    pytest.mark.unit,
]


class Test_ECSDeploymentWaiter:
    def _get_waiter(self, ecs_client: ECSClient) -> ECSDeploymentWaiter:
        mocked_session = mock.MagicMock()
        mocked_session.client.return_value = ecs_client
        return ECSDeploymentWaiter(ECSServiceRef("my-cluster", "my-service"), session=mocked_session)

    def test_get_latest_deployment_arn(self) -> None:
        # Arrange
        ecs = boto3.client("ecs")
        waiter = self._get_waiter(ecs)
        stubber = Stubber(ecs)
        for _ in range(2):
            stubber.add_response(
                "list_service_deployments",
                {"serviceDeployments": []},
                expected_params={
                    "cluster": "my-cluster",
                    "service": "my-service",
                    "status": ["PENDING", "IN_PROGRESS"],
                },
            )

        stubber.add_response(
            "list_service_deployments",
            {
                "serviceDeployments": [
                    {
                        "serviceDeploymentArn": "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1",  # noqa: E501
                        "startedAt": datetime(2025, 5, 22, 17, 59, 58, 808000),  # noqa: DTZ001
                        "status": "PENDING",
                    },
                ],
            },
            expected_params={
                "cluster": "my-cluster",
                "service": "my-service",
                "status": ["PENDING", "IN_PROGRESS"],
            },
        )

        # Act & Assert
        with stubber:
            assert (
                waiter.get_latest_deployment_arn(wait_for_start=True, polling_interval=1, max_attempts=3)
                == "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1"  # noqa: E501
            )

    def test_get_latest_deployment_arn_no_deployment(self) -> None:
        """If there is no deployment, it should raise `NoRunningDeploymentError`."""
        # Arrange
        ecs = boto3.client("ecs")
        waiter = self._get_waiter(ecs)
        stubber = Stubber(ecs)
        stubber.add_response(
            "list_service_deployments",
            {"serviceDeployments": []},
            expected_params={
                "cluster": "my-cluster",
                "service": "my-service",
                "status": ["PENDING", "IN_PROGRESS"],
            },
        )

        # Act & Assert
        with stubber, pytest.raises(NoRunningDeploymentError):
            waiter.get_latest_deployment_arn(wait_for_start=False)

    def test_get_latest_deployment_arn_max_attempts_exceeded(self) -> None:
        """If there is no deployment after max attempts, it should raise `NoRunningDeploymentError`."""
        # Arrange
        ecs = boto3.client("ecs")
        waiter = self._get_waiter(ecs)
        stubber = Stubber(ecs)
        for _ in range(5):
            stubber.add_response(
                "list_service_deployments",
                {"serviceDeployments": []},
                expected_params={
                    "cluster": "my-cluster",
                    "service": "my-service",
                    "status": ["PENDING", "IN_PROGRESS"],
                },
            )

        # Act & Assert
        with stubber, pytest.raises(NoRunningDeploymentError):
            assert (
                waiter.get_latest_deployment_arn(wait_for_start=True, polling_interval=1, max_attempts=3)
                == "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1"  # noqa: E501
            )

    def test_wait_for_deployment_complete(self) -> None:
        # Arrange
        ecs = boto3.client("ecs")
        waiter = self._get_waiter(ecs)
        stubber = Stubber(ecs)
        stubber.add_response(
            "describe_service_deployments",
            {"serviceDeployments": [{"status": "PENDING"}]},
            expected_params={
                "serviceDeploymentArns": [
                    "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1",
                ],
            },
        )
        stubber.add_response(
            "describe_service_deployments",
            {"serviceDeployments": [{"status": "IN_PROGRESS"}]},
            expected_params={
                "serviceDeploymentArns": [
                    "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1",
                ],
            },
        )
        stubber.add_response(
            "describe_service_deployments",
            {"serviceDeployments": [{"status": "SUCCESSFUL"}]},
            expected_params={
                "serviceDeploymentArns": [
                    "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1",
                ],
            },
        )

        # Act
        with stubber:
            ok, actual = waiter.wait_for_deployment_complete(
                "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1",
                polling_interval=1,
                max_attempts=3,
            )

        # Assert
        assert ok is True
        assert actual == "SUCCESSFUL"

    def test_wait_for_deployment_complete_max_attempts_exceeded(self) -> None:
        """If the deployment is still in incomplete status after max attempts, it should return `False` and last status."""  # noqa: E501
        # Arrange
        ecs = boto3.client("ecs")
        waiter = self._get_waiter(ecs)
        stubber = Stubber(ecs)
        stubber.add_response(
            "describe_service_deployments",
            {"serviceDeployments": [{"status": "PENDING"}]},
            expected_params={
                "serviceDeploymentArns": [
                    "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1",
                ],
            },
        )
        for _ in range(4):
            stubber.add_response(
                "describe_service_deployments",
                {"serviceDeployments": [{"status": "IN_PROGRESS"}]},
                expected_params={
                    "serviceDeploymentArns": [
                        "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1",
                    ],
                },
            )

        # Act
        with stubber:
            ok, actual = waiter.wait_for_deployment_complete(
                "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1",
                polling_interval=1,
                max_attempts=3,
            )

        # Assert
        assert ok is False
        assert actual == "IN_PROGRESS"

    @pytest.mark.parametrize(
        "status",
        [
            "STOPPED",
            "STOP_REQUESTED",
            "ROLLBACK_REQUESTED",
            "ROLLBACK_IN_PROGRESS",
            "ROLLBACK_SUCCESSFUL",
            "ROLLBACK_FAILED",
        ],
    )
    def test_wait_for_deployment_complete_failed(self, status: str) -> None:
        """If the deployment is in a failed status, it should return `False` with the status."""
        # Arrange
        ecs = boto3.client("ecs")
        waiter = self._get_waiter(ecs)
        stubber = Stubber(ecs)
        for _ in range(2):
            stubber.add_response(
                "describe_service_deployments",
                {"serviceDeployments": [{"status": "IN_PROGRESS"}]},
                expected_params={
                    "serviceDeploymentArns": [
                        "arn:aws:ecs:us-east-1:123456789012:service-deployment/example-cluster/example-service/ejGvqq2ilnbKT9qj0vLJe",
                    ],
                },
            )

        stubber.add_response(
            "describe_service_deployments",
            {"serviceDeployments": [{"status": status}]},
            expected_params={
                "serviceDeploymentArns": [
                    "arn:aws:ecs:us-east-1:123456789012:service-deployment/example-cluster/example-service/ejGvqq2ilnbKT9qj0vLJe",
                ],
            },
        )

        # Act
        with stubber:
            ok, actual = waiter.wait_for_deployment_complete(
                "arn:aws:ecs:us-east-1:123456789012:service-deployment/example-cluster/example-service/ejGvqq2ilnbKT9qj0vLJe",
                polling_interval=1,
                max_attempts=3,
            )

        # Assert
        assert ok is False
        assert actual == status

    def test_wait_for_service_stability(self) -> None:
        # Arrange
        ecs = boto3.client("ecs")
        waiter = self._get_waiter(ecs)
        stubber = Stubber(ecs)
        stubber.add_response(
            "describe_services",
            {
                "services": [
                    {
                        "status": "ACTIVE",
                        "desiredCount": 1,
                        "runningCount": 0,
                        "deployments": [
                            # ...
                            {},
                        ],
                    },
                ],
            },
            expected_params={"cluster": "my-cluster", "services": ["my-service"]},
        )
        for _ in range(2):
            stubber.add_response(
                "describe_services",
                {
                    "services": [
                        {
                            "desiredCount": 1,
                            "runningCount": 1,
                            "deployments": [
                                # ...
                                {},
                            ],
                        },
                    ],
                },
                expected_params={"cluster": "my-cluster", "services": ["my-service"]},
            )

        # Act
        with stubber:
            ok = waiter.wait_for_service_stability(polling_interval=1, max_attempts=3)

        # Assert
        assert ok is True

    def test_wait_for_service_stability_max_attempts_exceeded(self) -> None:
        # Arrange
        ecs = boto3.client("ecs")
        waiter = self._get_waiter(ecs)
        stubber = Stubber(ecs)
        for _ in range(5):
            stubber.add_response(
                "describe_services",
                {
                    "services": [
                        {
                            "desiredCount": 1,
                            "runningCount": 0,
                            "deployments": [
                                # ...
                                {},
                            ],
                        },
                    ],
                },
                expected_params={"cluster": "my-cluster", "services": ["my-service"]},
            )

        # Act
        with stubber:
            ok = waiter.wait_for_service_stability(polling_interval=1, max_attempts=3)

        # Assert
        assert ok is False

    def test_check_service_task_definition_is(self) -> None:
        # Arrange
        ecs = boto3.client("ecs")
        waiter = self._get_waiter(ecs)
        stubber = Stubber(ecs)
        stubber.add_response(
            "describe_services",
            {
                "services": [
                    {"taskDefinition": "arn:aws:ecs:ap-northeast-2:000000000000:task-definition/my-task-def:1"},
                ],
            },
            expected_params={
                "cluster": "my-cluster",
                "services": ["my-service"],
            },
        )

        # Act
        with stubber:
            ok, actual = waiter.check_service_task_definition_is(
                "arn:aws:ecs:ap-northeast-2:000000000000:task-definition/my-task-def:1",
            )

        # Assert
        assert ok is True
        assert actual == "arn:aws:ecs:ap-northeast-2:000000000000:task-definition/my-task-def:1"

    def test_check_service_task_definition_is_not(self) -> None:
        # Arrange
        ecs = boto3.client("ecs")
        waiter = self._get_waiter(ecs)
        stubber = Stubber(ecs)
        stubber.add_response(
            "describe_services",
            {
                "services": [
                    {"taskDefinition": "arn:aws:ecs:ap-northeast-2:000000000000:task-definition/my-task-def:2"},
                ],
            },
            expected_params={
                "cluster": "my-cluster",
                "services": ["my-service"],
            },
        )

        # Act
        with stubber:
            ok, actual = waiter.check_service_task_definition_is(
                "arn:aws:ecs:ap-northeast-2:000000000000:task-definition/my-task-def:1",
            )

        # Assert
        assert ok is False
        assert actual == "arn:aws:ecs:ap-northeast-2:000000000000:task-definition/my-task-def:2"

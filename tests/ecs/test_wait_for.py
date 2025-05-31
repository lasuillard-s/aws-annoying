from __future__ import annotations

from datetime import datetime
from unittest import mock

import boto3
import pytest
from botocore.stub import Stubber

from aws_annoying.ecs import (
    ECSServiceRef,
    NoRunningDeploymentError,
    wait_for_deployment_complete,
    wait_for_deployment_start,
    wait_for_service_stability,
)

pytestmark = [
    pytest.mark.unit,
]


class Test_wait_for_deployment_start:
    def test_wait_for_deployment_start(self) -> None:
        # Arrange
        mocked_session = mock.MagicMock()
        mocked_session.client.return_value = ecs = boto3.client("ecs")
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
                wait_for_deployment_start(
                    ECSServiceRef(cluster="my-cluster", service="my-service"),
                    session=mocked_session,
                    wait_for_start=True,
                    polling_interval=1,
                    max_attempts=3,
                )
                == "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1"  # noqa: E501
            )

    def test_wait_for_deployment_start_no_deployment(self) -> None:
        """If there is no deployment, it should raise `NoRunningDeploymentError`."""
        # Arrange
        mocked_session = mock.MagicMock()
        mocked_session.client.return_value = ecs = boto3.client("ecs")
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
            wait_for_deployment_start(
                ECSServiceRef(cluster="my-cluster", service="my-service"),
                session=mocked_session,
                wait_for_start=False,
            )

    def test_wait_for_deployment_start_max_attempts_exceeded(self) -> None:
        """If there is no deployment after max attempts, it should raise `NoRunningDeploymentError`."""
        # Arrange
        mocked_session = mock.MagicMock()
        mocked_session.client.return_value = ecs = boto3.client("ecs")
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
            wait_for_deployment_start(
                ECSServiceRef(cluster="my-cluster", service="my-service"),
                session=mocked_session,
                wait_for_start=True,
                polling_interval=1,
                max_attempts=3,
            )


class Test_wait_for_deployment_complete:
    def test_wait_for_deployment_complete(self) -> None:
        # Arrange
        mocked_session = mock.MagicMock()
        mocked_session.client.return_value = ecs = boto3.client("ecs")
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
            ok, actual = wait_for_deployment_complete(
                "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1",
                session=mocked_session,
                polling_interval=1,
                max_attempts=3,
            )

        # Assert
        assert ok is True
        assert actual == "SUCCESSFUL"

    def test_wait_for_deployment_complete_max_attempts_exceeded(self) -> None:
        """If the deployment is still in incomplete status after max attempts, it should return `False` and last status."""  # noqa: E501
        # Arrange
        mocked_session = mock.MagicMock()
        mocked_session.client.return_value = ecs = boto3.client("ecs")
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
            ok, actual = wait_for_deployment_complete(
                "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1",
                session=mocked_session,
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
        mocked_session = mock.MagicMock()
        mocked_session.client.return_value = ecs = boto3.client("ecs")
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
            ok, actual = wait_for_deployment_complete(
                "arn:aws:ecs:us-east-1:123456789012:service-deployment/example-cluster/example-service/ejGvqq2ilnbKT9qj0vLJe",
                session=mocked_session,
                polling_interval=1,
                max_attempts=3,
            )

        # Assert
        assert ok is False
        assert actual == status


class Test_wait_for_service_stability:
    def test_wait_for_service_stability(self) -> None:
        # Arrange
        mocked_session = mock.MagicMock()
        mocked_session.client.return_value = ecs = boto3.client("ecs")
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
            ok = wait_for_service_stability(
                ECSServiceRef(cluster="my-cluster", service="my-service"),
                session=mocked_session,
                polling_interval=1,
                max_attempts=3,
            )

        # Assert
        assert ok is True

    def test_wait_for_service_stability_max_attempts_exceeded(self) -> None:
        # Arrange
        mocked_session = mock.MagicMock()
        mocked_session.client.return_value = ecs = boto3.client("ecs")
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
            ok = wait_for_service_stability(
                ECSServiceRef(cluster="my-cluster", service="my-service"),
                session=mocked_session,
                polling_interval=1,
                max_attempts=3,
            )

        # Assert
        assert ok is False

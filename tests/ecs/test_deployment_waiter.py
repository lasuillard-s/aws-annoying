from datetime import datetime
from unittest import mock

import boto3
import pytest
from botocore.stub import Stubber

from aws_annoying.ecs import ECSDeploymentWaiter
from aws_annoying.ecs.common import ECSServiceRef
from aws_annoying.ecs.errors import NoRunningDeploymentError


class Test_ECSDeploymentWaiter:
    def test_get_latest_deployment_arn(self) -> None:
        # Arrange
        mocked_session = mock.MagicMock()
        ecs = boto3.client("ecs")
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
                        "serviceArn": "arn:aws:ecs:ap-northeast-2:000000000000:service/my-cluster/my-service",
                        "clusterArn": "arn:aws:ecs:ap-northeast-2:000000000000:cluster/my-cluster",
                        "startedAt": datetime(2025, 5, 22, 17, 59, 58, 808000),  # noqa: DTZ001
                        "createdAt": datetime(2025, 5, 22, 17, 59, 58, 33000),  # noqa: DTZ001
                        "finishedAt": datetime(2025, 5, 22, 18, 0, 34, 738000),  # noqa: DTZ001
                        "targetServiceRevisionArn": "arn:aws:ecs:ap-northeast-2:000000000000:service-revision/my-cluster/my-service/2977184796286556598",  # noqa: E501
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
        mocked_session.client.return_value = ecs
        waiter = ECSDeploymentWaiter(ECSServiceRef("my-cluster", "my-service"), session=mocked_session)

        # Act & Assert
        with stubber:
            assert (
                waiter.get_latest_deployment_arn(wait_for_start=True, polling_interval=1, max_attempts=3)
                == "arn:aws:ecs:ap-northeast-2:000000000000:service-deployment/my-cluster/my-service/wAMeGIKKhxAmoq1Ef03r1"  # noqa: E501
            )

    def test_get_latest_deployment_arn_no_deployment(self) -> None:
        # Arrange
        mocked_session = mock.MagicMock()
        ecs = boto3.client("ecs")
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
        mocked_session.client.return_value = ecs
        waiter = ECSDeploymentWaiter(ECSServiceRef("my-cluster", "my-service"), session=mocked_session)

        # Act & Assert
        with stubber, pytest.raises(NoRunningDeploymentError):
            waiter.get_latest_deployment_arn(wait_for_start=False)

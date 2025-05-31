from __future__ import annotations

from unittest import mock

import boto3
import pytest
from botocore.stub import Stubber

from aws_annoying.ecs import ECSServiceRef, check_service_task_definition

pytestmark = [
    pytest.mark.unit,
]


class Test_check_service_task_definition:
    def test_success(self) -> None:
        # Arrange
        mocked_session = mock.MagicMock()
        mocked_session.client.return_value = ecs = boto3.client("ecs")
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
            ok, actual = check_service_task_definition(
                ECSServiceRef(cluster="my-cluster", service="my-service"),
                expect="arn:aws:ecs:ap-northeast-2:000000000000:task-definition/my-task-def:1",
                session=mocked_session,
            )

        # Assert
        assert ok is True
        assert actual == "arn:aws:ecs:ap-northeast-2:000000000000:task-definition/my-task-def:1"

    def test_not_matching(self) -> None:
        # Arrange
        mocked_session = mock.MagicMock()
        mocked_session.client.return_value = ecs = boto3.client("ecs")
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
            ok, actual = check_service_task_definition(
                ECSServiceRef(cluster="my-cluster", service="my-service"),
                expect="arn:aws:ecs:ap-northeast-2:000000000000:task-definition/my-task-def:1",
                session=mocked_session,
            )

        # Assert
        assert ok is False
        assert actual == "arn:aws:ecs:ap-northeast-2:000000000000:task-definition/my-task-def:2"

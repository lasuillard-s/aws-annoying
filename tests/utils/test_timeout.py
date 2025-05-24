from __future__ import annotations

from time import sleep

import pytest

from aws_annoying.utils.timeout import OperationTimeoutError, Timeout
from tests._helpers import run_if_windows, skip_if_windows


class Test_Timeout:
    @skip_if_windows
    def test_decorator_non_windows(self) -> None:
        # Arrange
        @Timeout(1)
        def do_something() -> None:
            sleep(3)

        # Act & Assert
        with pytest.raises(OperationTimeoutError):
            do_something()

    @skip_if_windows
    def test_context_manager_non_windows(self) -> None:
        # Arrange & Act & Assert
        with Timeout(1), pytest.raises(OperationTimeoutError):
            sleep(3)

    @run_if_windows
    def test_decorator_windows(self) -> None:
        # Arrange
        @Timeout(1)
        def do_something() -> None:
            sleep(3)

        # Act & Assert
        do_something()  # Won't raise an exception

    @run_if_windows
    def test_context_manager_windows(self) -> None:
        # Arrange & Act & Assert
        with Timeout(1):
            sleep(3)  # Won't raise an exception

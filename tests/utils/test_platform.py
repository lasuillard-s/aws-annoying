from __future__ import annotations

import pytest

from aws_annoying.utils.platform import is_windows


class Test_command_as_root:
    pass


class Test_is_root:
    pass


class Test_os_release:
    pass


class Test_is_windows:
    def test_linux(self) -> None:
        assert is_windows() is False

    @pytest.mark.macos
    def test_macos(self) -> None:
        assert is_windows() is False

    @pytest.mark.windows
    def test_windows(self) -> None:
        assert is_windows() is True

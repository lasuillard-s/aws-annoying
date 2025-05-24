import pytest

from aws_annoying.utils.platform import is_windows

skip_if_windows = pytest.mark.skipif(is_windows(), reason="Test is skipped on Windows OS.")
run_if_windows = pytest.mark.skipif(not is_windows(), reason="Test is skipped on non-Windows OS.")

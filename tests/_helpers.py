import os

import pytest

from aws_annoying.utils.platform import is_macos, is_windows

# Test runner environment
ci_only = pytest.mark.skipif(not os.environ.get("CI", None), reason="This test only run in CI.")

# macOS-specific
skip_if_macos = pytest.mark.skipif(is_macos(), reason="Test is skipped on macOS.")
run_if_macos = pytest.mark.skipif(not is_macos(), reason="Test run only on macOS.")

# Windows-specific
skip_if_windows = pytest.mark.skipif(is_windows(), reason="Test is skipped on Windows OS.")
run_if_windows = pytest.mark.skipif(not is_windows(), reason="Test run only on Windows OS.")

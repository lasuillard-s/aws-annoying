from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Automatically add the 'cli' marker to all tests under tests/_cli/."""
    for item in items:
        item.add_marker(pytest.mark.cli)

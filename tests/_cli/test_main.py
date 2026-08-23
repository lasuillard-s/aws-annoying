from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aws_annoying._cli import main

pytestmark = [
    pytest.mark.unit,
]


def test_entrypoint_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entrypoint calls app when app is defined."""
    # Arrange
    mock_app = MagicMock()
    monkeypatch.setattr(main, "app", mock_app)

    # Act
    main.entrypoint()

    # Assert
    mock_app.assert_called_once()


def test_entrypoint_missing_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entrypoint exits with informative error message when app is None."""
    # Arrange
    monkeypatch.setattr(main, "app", None)

    # Act & Assert
    with pytest.raises(SystemExit, match="CLI dependencies are missing"):
        main.entrypoint()

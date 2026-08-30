import builtins
import importlib
from typing import Any
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


def test_main_import_without_typer(monkeypatch: pytest.MonkeyPatch) -> None:
    """When typer cannot be imported, main.app is set to None."""
    # Arrange
    orig_import = builtins.__import__

    def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "typer":
            msg = "No module named 'typer'"
            raise ImportError(msg)

        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    # Act
    reloaded = importlib.reload(main)

    # Assert
    try:
        assert reloaded.app is None
    finally:
        monkeypatch.undo()
        importlib.reload(main)

from __future__ import annotations

from pathlib import Path

import pytest
import toml
from typer.testing import CliRunner

from aws_annoying.cli.main import app

runner = CliRunner()

pytestmark = [
    pytest.mark.unit,
]


def test_version() -> None:
    """Show version with `--version` top-level argument."""
    # Arrange
    pyproject = toml.load(Path(__file__).parent.parent.parent / "pyproject.toml")
    current_version = pyproject["project"]["version"]

    # Act
    result = runner.invoke(
        app,
        [
            "--version",
        ],
    )

    # Assert
    assert result.exit_code == 0
    assert result.stdout.strip() == current_version

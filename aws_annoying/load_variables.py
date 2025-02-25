from __future__ import annotations

from rich import print  # noqa: A004


def load_variables() -> None:
    """Load variables from AWS parameter store and secrets manager."""
    print("Loading variables...")

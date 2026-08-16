from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import typer
from prompt_toolkit.shortcuts import radiolist_dialog

if TYPE_CHECKING:
    from collections.abc import Sequence

T = TypeVar("T")


def prompt_select(title: str, choices: Sequence[tuple[T, str]]) -> T:
    """Prompt user to select one of the choices interactively.

    Args:
        title: The title of the prompt.
        choices: A sequence of tuples (value, label).

    Returns:
        The selected value.
    """
    result = radiolist_dialog(
        title=title,
        text="Please select an option:",
        values=[(choice[0], choice[1]) for choice in choices],
    ).run()
    if result is None:
        raise typer.Exit
    return result

# TODO(lasuillard): Using this file until split CLI from library codebase
from __future__ import annotations

from typing import Any

import typer
from rich.prompt import Confirm

from .session_manager import SessionManager as _SessionManager


# Custom session manager with console interactivity
class SessionManager(_SessionManager):
    def __init__(self, *args: Any, confirm: bool, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._confirm = confirm

    def before_install(self, command: list[str]) -> None:
        if self._confirm:
            return

        confirm = Confirm.ask(f"⚠️ Will run the following command: [bold red]{' '.join(command)}[/bold red]. Proceed?")
        if not confirm:
            raise typer.Abort

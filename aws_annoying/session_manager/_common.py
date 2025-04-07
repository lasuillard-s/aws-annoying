# TODO(lasuillard): Using this file until split CLI from library codebase
from __future__ import annotations

import typer
from rich.prompt import Confirm

from .session_manager import SessionManager as _SessionManager


# Custom session manager with console interactivity
class SessionManager(_SessionManager):
    def before_install(self, command: list[str]) -> None:
        confirm = Confirm.ask(f"⚠️ Will run the following command: [bold red]{' '.join(command)}[/bold red]. Proceed?")
        if not confirm:
            raise typer.Abort

from __future__ import annotations

from typing import Any

import typer
from rich.prompt import Confirm

from aws_annoying.session_manager import SessionManager as _SessionManager


# Custom session manager with console interactivity
class SessionManager(_SessionManager):
    def before_install(self, command: list[str]) -> None:
        if self._confirm:
            return

        confirm = Confirm.ask(f"Will run the following command: [bold red]{' '.join(command)}[/bold red]. Proceed?")
        if not confirm:
            raise typer.Abort

    def install(self, *args: Any, confirm: bool = False, **kwargs: Any) -> None:
        self._confirm = confirm
        return super().install(*args, **kwargs)

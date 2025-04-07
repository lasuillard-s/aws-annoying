from __future__ import annotations

import typer
from rich import print  # noqa: A004
from rich.prompt import Confirm

from aws_annoying.utils.downloader import TQDMDownloader

from ._app import session_manager_app
from .session_manager import SessionManager


# https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html
@session_manager_app.command()
def install(
    # TODO(lasuillard): Will add options: --os, --arch, --skip-verify, --dry-run
) -> None:
    """Install AWS Session Manager plugin."""
    session_manager = _SessionManager(downloader=TQDMDownloader())

    # Check session-manager-plugin already installed
    is_installed, binary_path, version = session_manager.verify_installation()
    if is_installed:
        print(f"✅ Session Manager plugin is already installed at {binary_path} (version: {version})")
        return

    # Install session-manager-plugin
    print("⬇️ Installing AWS Session Manager plugin. You could be prompted for admin privileges request.")
    session_manager.install()

    # Verify installation
    is_installed, binary_path, version = session_manager.verify_installation()
    if not is_installed:
        print("❌ Installation failed. Session Manager plugin not found.")
        raise typer.Exit(1)

    print(f"✅ Session Manager plugin successfully installed at {binary_path} (version: {version})")


# Add console interactivity to session manager installation steps
class _SessionManager(SessionManager):
    def before_install(self, command: list[str]) -> None:
        confirm = Confirm.ask(f"⚠️ Will run the following command: [bold red]{' '.join(command)}[/bold red]. Proceed?")
        if not confirm:
            raise typer.Abort

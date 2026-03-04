from __future__ import annotations

import logging

import typer

from aws_annoying.utils.downloader import TQDMDownloader

from ._app import session_manager_app
from ._common import SessionManager

logger = logging.getLogger(__name__)


# https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html
@session_manager_app.command()
def install(
    ctx: typer.Context,
    *,
    yes: bool = typer.Option(
        False,  # noqa: FBT003
        help="Do not ask confirmation for installation.",
    ),
) -> None:
    """Install AWS Session Manager plugin."""
    dry_run = ctx.meta["dry_run"]
    session_manager = SessionManager()

    # Check session-manager-plugin already installed
    is_installed, binary_path, version = session_manager.verify_installation()
    if is_installed:
        logger.info("Session Manager plugin is already installed at %s (version: %s)", binary_path, version)
        return

    # Install session-manager-plugin
    logger.warning("Installing AWS Session Manager plugin. You could be prompted for admin privileges request.")
    if not dry_run:
        session_manager.install(confirm=yes, downloader=TQDMDownloader())

    # Verify installation
    is_installed, binary_path, version = session_manager.verify_installation()
    if not is_installed:
        logger.error("Installation failed. Session Manager plugin not found.")
        raise typer.Exit(1)

    logger.info("Session Manager plugin successfully installed at %s (version: %s)", binary_path, version)

class SessionManagerError(Exception):
    """Base exception for all errors related to Session Manager."""


class PluginNotInstalledError(SessionManagerError):
    """Trying to use the Session Manager plugin before it is installed."""

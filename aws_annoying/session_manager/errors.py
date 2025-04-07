class SessionManagerError(Exception):
    """Base exception for all errors related to Session Manager."""


class UnsupportedPlatformError(SessionManagerError):
    """Exception raised when the platform is not supported."""


class PluginNotInstalledError(SessionManagerError):
    """Trying to use the Session Manager plugin before it is installed."""

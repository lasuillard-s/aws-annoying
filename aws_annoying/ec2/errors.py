class EC2Error(Exception):
    """Base class for all EC2 module errors."""


class InstanceNotReadyError(EC2Error):
    """EC2 instance failed to become ready within the maximum attempts."""


class InvalidInstanceIdError(EC2Error):
    """EC2 instance ID format is invalid."""


class InstanceNotFoundError(EC2Error):
    """EC2 instance was not found."""


class MultipleInstancesFoundError(EC2Error):
    """Multiple EC2 instances were found when only one was expected."""

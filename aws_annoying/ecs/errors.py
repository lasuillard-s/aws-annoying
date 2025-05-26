class WaitForDeploymentError(Exception):
    """Base class for all deployment waiter errors."""


class NoRunningDeploymentError(WaitForDeploymentError):
    """No running deployment found for the service."""


class DeploymentFailedError(WaitForDeploymentError):
    """Deployment failed."""


class ServiceTaskDefinitionAssertionError(WaitForDeploymentError):
    """Service task definition does not match the expected one."""

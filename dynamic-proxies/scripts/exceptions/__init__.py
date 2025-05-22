class DeploymentException(Exception):
    """Raised when a deployment fails"""

    pass


class ServiceException(Exception):
    """Raised when a service fails"""

    pass


class VirtualServiceException(Exception):
    """Raised when a virtual service fails"""

    pass


class PodException(Exception):
    """Raised when pod(s) fails"""

    pass

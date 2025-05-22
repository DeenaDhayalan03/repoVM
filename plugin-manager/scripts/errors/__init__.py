class ILensErrors(Exception):
    """Generic iLens Error"""

    def __init__(self, message="An error has occurred. Please contact support."):
        self.message = message
        super().__init__(self.message)


class AuthenticationError(ILensErrors):
    pass


class ErrorMessages:
    UNKNOWN_ERROR = "Unknown Error Occurred"
    OP_FAILED = "Operation failed"
    # Authorization Errors
    ERROR_AUTH_FAILED = "Authentication Failed. Please verify token"
    ERROR_SIG_EXP = "Signature Expired"
    ERROR_SIG_INV = "Signature Not Valid"
    NO_KEY_ERROR = "No key pair defined for user, create key to sign."
    KEY_CREATE_FAILED = "Key creation failed. Check your inputs or contact support."
    D_ID_NOT_FOUND = "No key pairs found for given DID."
    INVALID_SIGNATURE_ID = "Signature ID is invalid, please check input."


class PluginNotFoundError(ILensErrors):
    """
    Raise when plugin ID is invalid or not found
    """


class PluginAlreadyExistError(ILensErrors):
    """
    Raise when plugin is already there with same name
    """


class ProxyKeyNotFoundError(ILensErrors):
    """
    Raise when proxy key is not found
    """


class UserNotFound(ILensErrors):
    """
    Raise when user is not found
    """


class AlreadyDeployedError(ILensErrors):
    """
    Raise when its already deployed
    """


class DeploymentException(ILensErrors):
    """
    Raise when deployment fails
    """


class ManifestError(ILensErrors):
    """
    Raise when manifest file is not found
    """


class PluginResourceException(ILensErrors):
    """
    Raise when plugin resource is beyond or below the limit
    """


class AntiVirusScanFailed(ILensErrors):
    """
    Raise when antivirus scan fails
    """


class SonarqubeScanFailed(ILensErrors):
    """
    Raise when sonarqube scan fails
    """


class KubeflowPipelineConfigNotFound(ILensErrors):
    """
    Raise when Kubeflow Pipeline Config is not found
    """


class CRONExpressionError(ILensErrors):
    """
    Raise when CRON Expression is not valid
    """


class ContentTypeError(ILensErrors):
    """
    Raise when Content Type is not valid
    """


class VerficiationError(ILensErrors):
    """
    Raise when verification fails
    """

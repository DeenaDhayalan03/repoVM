from pydantic_settings import BaseSettings

from scripts.config import EnvConf


class DatabaseNames:
    ilens_configuration = "ilens_configuration"


class CollectionNames:
    plugin_state = "plugin_state"


class VolumeMount:
    _host_path = {
        "name": "core-volumes",
        "hostPath": {"path": EnvConf.host_path, "type": "Directory"},
    }
    _persistent_volume_claim = {
        "name": "core-volumes",
        "persistentVolumeClaim": {"claimName": EnvConf.claim_name},
    }
    volume = _persistent_volume_claim if EnvConf.claim_name else _host_path


class _IgnoreSecrets(BaseSettings):
    secret_type: list[str] = ["kubernetes.io/service-account-token", "kubernetes.io/dockerconfigjson"]
    secret_list: list[str] = []


class ErrorMessages:
    error_reading_deployment = "Error reading deployment"


IgnoreSecrets = _IgnoreSecrets()

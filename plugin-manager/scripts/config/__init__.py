import os
import pathlib
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings
import tempfile

from scripts.constants.sonar_constants import sonarqube_constants

PROJECT_NAME = "ut_plugin_manager"


class _Services(BaseSettings):
    HOST: str = Field(default="0.0.0.0", validation_alias="service_host")
    PORT: int = Field(default=6789, validation_alias="service_port")
    SELF_PROXY: Optional[str] = Field(None, validation_alias="")
    LOG_LEVEL: Literal["INFO", "DEBUG", "ERROR", "QTRACE"] = "INFO"
    ENABLE_FILE_LOG: bool = False
    ENABLE_CONSOLE_LOG: bool = True
    SW_DOCS_URL: Optional[str] = None
    SW_OPENAPI_URL: Optional[str] = None
    SECURE_COOKIE: bool = True
    ENABLE_RBAC: bool = False
    DOCKER_HOST: str | None = "tcp://localhost:2375"
    PLUGIN_BUILD_ARGS: dict = {}
    HOME_LINK: Optional[str] = Field(None, env="HOME_LINK")
    KUBEFLOW_URL: str | None = None
    KUBEFLOW_MULTI_USER: bool | None = False


class _Databases(BaseSettings):
    MONGO_URI: str
    REDIS_URI: str
    REDIS_LOGIN_DB: int = 9
    REDIS_USER_ROLE_DB: int = 21
    REDIS_PROJECT_DB: int = 18


class _BasePathConf(BaseSettings):
    BASE_PATH: str = "/code/data"
    PROTOCOL_PLUGIN_COMMON_PATH: str = "protocol_plugins_directory/"
    FOLDER_MOUNT_PATH: str = "/code/temp"
    CODE_STORE_PATH: str = "/code/temp/code_store"
    TEMP_PATH: str = "/code/temp"
    LOCAL_IMAGE_PATH: str = "/code/data/plugin-manager/plugin_artifacts"
    ASSETS_FOLDER: str = "/code/assets"


class _PathConf:
    BASE_PATH: pathlib.Path = pathlib.Path(_BasePathConf().BASE_PATH)
    KEY_PATH: pathlib.Path = BASE_PATH / "keys"
    CODE_STORE_PATH: pathlib.Path = pathlib.Path(_BasePathConf().CODE_STORE_PATH)
    ASSETS_FOLDER: pathlib.Path = pathlib.Path(_BasePathConf().ASSETS_FOLDER)
    PROTOCOL_PLUGIN_COMMON_PATH: pathlib.Path = pathlib.Path(_BasePathConf().PROTOCOL_PLUGIN_COMMON_PATH)
    TEMP_PATH: pathlib.Path = pathlib.Path(_BasePathConf().TEMP_PATH)
    LOCAL_IMAGE_PATH: pathlib.Path = pathlib.Path(_BasePathConf().LOCAL_IMAGE_PATH)
    tempfile.tempdir = TEMP_PATH

    # create above path if those doesnt exists during intialization of this class without specifying each and every variable
    def __init__(self):
        for attr_name in dir(self):
            attr_value = getattr(self, attr_name)
            if (
                isinstance(attr_value, pathlib.Path)
                and not attr_value.exists()
                and attr_name not in ["ASSETS_FOLDER", "PROTOCOL_PLUGIN_COMMON_PATH"]
            ):
                attr_value.mkdir(parents=True, exist_ok=True)


class _Secrets(BaseSettings):
    LOCK_OUT_TIME_MINS: int = 30
    leeway_in_mins: int = 10
    unique_key: str = "45c37939-0f75"
    token: str = "8674cd1d-2578-4a62-8ab7-d3ee5f9a"
    issuer: str = "ilens"
    alg: str = "RS256"


class _ExternalServices(BaseSettings):
    PROXY_MANAGER_URL: str = Field(alias="DYNAMIC_PROXIES_URL")
    DCP_URL: str = Field(alias="DEVICE_CONTROL_PLANE_URL")


class _AzureCredentials(BaseSettings):
    azure_container_registry_url: str | None = Field(None, alias="PLUGINS_CONTAINER_REGISTRY_URL")
    azure_registry_username: str | None = Field(None, alias="PLUGINS_CONTAINER_REGISTRY_USERNAME")
    azure_registry_password: str | None = Field(None, alias="PLUGINS_CONTAINER_REGISTRY_PASSWORD")


class _MQTTConf(BaseSettings):
    MQTT_URL: str = Field(alias="MQTT_HOST")
    MQTT_PORT: int
    MQTT_USERNAME: str
    MQTT_PASSWORD: str
    publish_base_topic: str = "ilens/notifications"


class _VulnerabilityScanner(BaseSettings):
    VULNERABILITY_SCAN: bool = True
    VULNERABILITY_FOLDER_PATH: str = os.path.join(
        _BasePathConf().FOLDER_MOUNT_PATH, "plugin-manager/vulnerability-reports"
    )
    VULNERABILITY_SCAN_LEVEL: str = "CRITICAL,HIGH"
    REPORT_FOLDER_PATH: str = os.path.join(_BasePathConf().FOLDER_MOUNT_PATH, "plugin-manager/vulnerability-reports")
    ANTIVIRUS_SCAN: bool = True
    ANTIVIRUS_FOLDER_PATH: str = os.path.join(_BasePathConf().FOLDER_MOUNT_PATH, "plugin-manager/antivirus-reports")
    ANTIVIRUS_REPORT_FOLDER_PATH: str = os.path.join(
        _BasePathConf().FOLDER_MOUNT_PATH, "plugin-manager/antivirus-reports"
    )
    SONARQUBE_SCAN: bool = True
    ABSOLUTE_CODE_STORE_PATH: str = os.path.join(_BasePathConf().FOLDER_MOUNT_PATH, "code_store/pull_path")


class _ResourceConfig(BaseSettings):
    memory_request_lower_bound: float = 0
    memory_request_upper_bound: float = 16
    memory_limit_lower_bound: float = 0
    memory_limit_upper_bound: float = 16
    cpu_request_lower_bound: float = 0
    cpu_request_upper_bound: float = 8000
    cpu_limit_lower_bound: float = 0
    cpu_limit_upper_bound: float = 8
    replica_lower_bound: int = 0
    replica_upper_bound: int = 5


class _SonarQubeConfig(BaseSettings):
    sonarqube_url: str | None = "sonarqube.unifytwin.com"
    sonarqube_password: str | None = None
    sonarqube_user: str | None = None
    sonarqube_token: str | None = None
    code_smell_threshold: int = 100
    vulnerability_threshold: int = 0
    bug_threshold: int = 0
    code_smell_severity: str = sonarqube_constants["default_severity"]
    bug_severity: str = sonarqube_constants["default_severity"]
    vulnerability_severity: str = sonarqube_constants["default_severity"]


class _MinioSettings(BaseSettings):
    MINIO_ENDPOINT: str = "infra-minio.ilens-infra.svc.cluster.local:9000"
    MINIO_ACCESS_KEY: str = "minio"
    MINIO_SECRET_KEY: str = "minio123"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str = "plugins"


class _ContainerSigningSettings(BaseSettings):
    SIGNING_ENABLED: bool = True
    SIGNING_KEY_PATH: str = "/code/cosign/cosign.key"
    VERIFY_PUB_PATH: str = "/code/cosign/cosign.pub"
    ALLOW_INSECURE_REGISTRY: bool = False
    ALLOW_HTTP_REGISTRY: bool = False
    COSIGN_PASSWORD: str
    OUTPUT_SIGNATURE_PATH: pathlib.Path = pathlib.Path("/code/temp/output_signature")


class _DownloadDockerImage(BaseSettings):
    DOWNLOAD_IMAGE_ENABLED: bool = False


class _KubeflowPortal(BaseSettings):
    IMAGE_PULL_SECRET: str = "kl-azregistry"


Services = _Services()
Databases = _Databases()
PathConf = _PathConf()
Secrets = _Secrets()
ExternalServices = _ExternalServices()
MQTTConf = _MQTTConf()
AzureCredentials = _AzureCredentials()
VulnerabilityScanner = _VulnerabilityScanner()
ResourceConfig = _ResourceConfig()
SonarQubeConfig = _SonarQubeConfig()
MinioSettings = _MinioSettings()
ContainerSigningSettings = _ContainerSigningSettings()
DownloadDockerImage = _DownloadDockerImage()
KubeflowPortal = _KubeflowPortal()
__all__ = [
    "PROJECT_NAME",
    "Services",
    "Databases",
    "PathConf",
    "Secrets",
    "ExternalServices",
    "MQTTConf",
    "AzureCredentials",
    "VulnerabilityScanner",
    "ResourceConfig",
    "SonarQubeConfig",
    "MinioSettings",
    "ContainerSigningSettings",
    "DownloadDockerImage",
    "KubeflowPortal",
]

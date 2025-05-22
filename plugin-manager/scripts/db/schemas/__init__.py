from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel

from scripts.constants.ui_components import plugin_advance_config_header


class AdvanceConfig(BaseModel):
    headerContent: list = plugin_advance_config_header
    bodyContent: list = []


class SecurityChecks(BaseModel):
    antivirus: bool | None = None
    vulnerabilities: bool | None = None
    sonarqube: bool | None = None


class PluginMetaDBSchema(BaseModel):
    additional_fields: list = []
    base_executor: Literal["python"] = "python"
    configurations: dict | list = {}
    container_port: int = 80
    container_registry_credentials: dict | None = None
    container_registry_url: str | None = None
    deploy_as_container: bool = True
    deployed_by: str | None = None
    deployed_on: datetime | None = None
    deployment_status: Literal[
        "pending",
        "running",
        "failed",
        "deploying",
        "stopped",
        "success",
        "in progress",
        "scanning",
    ] = "pending"
    errors: list = []
    file_upload_path: str | None = None
    minio_file_path: str | None = None
    git_target_id: str | None = None
    git_repository: str | None = None
    git_access_token: str | None = None
    git_branch: str | None = None
    git_url: str | None = None
    git_username: str | None = None
    industry: list[str]
    information: dict[str, Any]
    name: str
    plugin_id: str
    plugin_type: str
    proxy: str = ""
    registration_type: str
    validation_message: str | None = None
    validation_status: bool | None = None
    version: str | float = 1.0
    advancedConfiguration: AdvanceConfig = AdvanceConfig()
    enable_plugin_report: bool = False
    security_checks: SecurityChecks | None = SecurityChecks()
    portal: bool = False
    current_version: str | float | None = None

    def __init__(self, **data):
        super().__init__(**data)
        self.version = self.change_version_to_float(self.version)
        self.current_version = self.change_version_to_float(self.current_version)

    @staticmethod
    def change_version_to_float(version: str | float) -> float:
        if isinstance(version, str):
            return float(version)
        return version


class PluginFetchResponse(BaseModel):
    additional_fields: list = []
    base_executor: Literal["python"] = "python"
    configurations: dict | list = {}
    deploy_as_container: bool = True
    deployed_by: str | None = None
    deployed_on: datetime | None = None
    deployment_status: Literal[
        "pending",
        "running",
        "failed",
        "deploying",
        "stopped",
        "success",
        "in progress",
        "scanning",
    ] = "pending"
    errors: list = []
    file_upload_path: str | None = None
    minio_file_path: str | None = None
    git_target_id: str | None = None
    git_repository: str | None = None
    git_access_token: str | None = None
    git_branch: str | None = None
    git_url: str | None = None
    git_username: str | None = None
    industry: list[str]
    information: dict[str, Any]
    name: str
    plugin_id: str
    plugin_type: str
    proxy: str = ""
    registration_type: str
    advancedConfiguration: AdvanceConfig = AdvanceConfig()
    validation_message: str | None = None
    validation_status: bool | None = None
    version: str | float
    security_checks: SecurityChecks | None = SecurityChecks()
    current_version: str | float = 1.0

    def __init__(self, **data):
        super().__init__(**data)
        self.version = self.change_version_to_float(self.version)
        self.current_version = self.change_version_to_float(self.current_version)

    @staticmethod
    def change_version_to_float(version: str | float) -> float:
        if isinstance(version, str):
            return float(version)
        return version


class WidgetPluginSchema(BaseModel):
    plugin_id: str
    widget_pl_id: str
    chart_type: str
    installed_on: float
    installed_by: str
    version: str | float = 1.0
    proxy: str
    data_source: list
    project_id: str
    category: str
    widget_type: list
    widget_category: list | None = None
    enable_plugin_report: bool = False
    meta: dict


class MicroservicePluginSchema(BaseModel):
    plugin_id: str
    installed_on: float
    installed_by: str
    version: str = "1.0"
    proxy: str
    data_source: Optional[str] = "git"


class CustomAppPluginSchema(BaseModel):
    plugin_id: str
    custom_app_id: str
    app_name: str
    installed_on: float
    installed_by: str
    version: str | float = 1.0
    base_proxy: str
    project_id: str
    meta: dict


class FormioComponentPluginSchema(BaseModel):
    plugin_id: str
    formio_component_id: str
    component_name: str
    installed_on: float
    installed_by: str
    version: str | float = 1.0
    base_proxy: str
    project_id: str
    meta: dict


class VulnerabilityReportSchema(BaseModel):
    Package: str | None = None
    PackageType: str | None = None
    Path: str | None = None
    InstalledVersion: str | None = None
    FixedVersion: str | None = None
    Severity: str | None = None
    Description: str | None = None

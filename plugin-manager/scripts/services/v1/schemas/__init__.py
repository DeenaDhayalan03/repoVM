import os
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, field_validator, model_validator

from scripts.config import AzureCredentials, ResourceConfig
from scripts.constants.schemas import AGGridTableRequest
from scripts.constants.ui_components import plugin_advance_config_header

STARTING_VALUE_ERROR = "Input Field-Value shouldn't start with a Special Character.."
STRING_VALUE_ERROR = "Input Field Consists of Unsupported Special Character..."
STARTING_VALIDATION = set(os.environ.get("STRING_VALIDATION_LIST1", default="=,<,+,!,@,%").split(","))
STRING_VALIDATION = set(os.environ.get("STRING_VALIDATION_LIST2", default="<,=,>,%").split(","))


# Define a base class with the common validator
class BaseValidatorModel(BaseModel):
    @field_validator("*", mode="before")
    def validate_input_fields(cls, model_value):
        str_starting_validation(model_value)
        if model_value and isinstance(model_value, dict):
            for _each_key, each_value in model_value.items():
                str_starting_validation(each_value)
                if each_value and isinstance(each_value, dict):
                    for _key, value in each_value.items():
                        str_starting_validation(value)
        return model_value


def str_starting_validation(value):
    if value and isinstance(value, str):
        if value[0] in STARTING_VALIDATION:
            raise ValueError(STARTING_VALUE_ERROR)
        elif any(ext in value for ext in STRING_VALIDATION):
            raise ValueError(STRING_VALUE_ERROR)


class STATUS:
    SUCCESS = "success"
    FAILED = "failed"
    SUCCESS_CODES = [200, 201]


class DefaultResponse(BaseModel):
    status: str = STATUS.SUCCESS
    message: str | None = None
    data: Any = None


class DefaultFailureResponse(DefaultResponse):
    status: str = STATUS.FAILED
    error: Any = None


class DefaultFailureResponseGit(BaseModel):
    status: str = "failed"
    message: str
    error: Optional[Any] = None


class ResourceConfigModel(BaseModel):
    property: str = ""
    description: str = ""
    propertyLabel: str = ""
    input: float | int = 0

    @model_validator(mode="before")
    def validate_input(cls, values):
        property_name = values.get("property")
        input_value = values["input"]

        if property_name == "replicas":
            validate_input_range(input_value, ResourceConfig.replica_upper_bound, ResourceConfig.replica_lower_bound)
        elif property_name == "cpu_request":
            validate_input_range(
                input_value, ResourceConfig.cpu_request_upper_bound, ResourceConfig.cpu_request_lower_bound
            )
        elif property_name == "cpu_limit":
            validate_input_range(
                input_value, ResourceConfig.cpu_limit_upper_bound, ResourceConfig.cpu_limit_lower_bound
            )
        elif property_name == "memory_request":
            validate_input_range(
                input_value, ResourceConfig.memory_request_upper_bound, ResourceConfig.memory_request_lower_bound
            )
        elif property_name == "memory_limit":
            validate_input_range(
                input_value, ResourceConfig.memory_limit_upper_bound, ResourceConfig.memory_limit_lower_bound
            )

        return values


def validate_input_range(input_value, upper_bound, lower_bound):
    if input_value > upper_bound:
        raise ValueError(f"Input value should be less than {upper_bound}")
    elif input_value < lower_bound:
        raise ValueError(f"Input value should be greater than {lower_bound}")


class AdvanceConfig(BaseModel):
    headerContent: list = plugin_advance_config_header
    bodyContent: list[ResourceConfigModel] = []


class Plugin(BaseValidatorModel):
    plugin_id: str | None = None
    name: str
    plugin_type: str
    industry: Optional[list] = []
    registration_type: str
    base_executor: Literal["python"] = "python"
    configurations: dict | list = {}
    information: dict[str, Any]
    git_target_id: str | None = None
    git_repository: str | None = None
    git_target_name: str | None = None
    git_url: str | None = None
    git_branch: str | None = None
    git_username: str | None = None
    git_access_token: str | None = None
    container_port: int = 80
    additional_fields: list = []
    validation_status: bool | None = None
    validation_message: str | None = None
    advancedConfiguration: AdvanceConfig = AdvanceConfig()
    enable_plugin_report: bool = False
    portal: bool = False
    version: str | float = 1.0
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


class DeployPlugin(BaseModel):
    plugin_id: str
    deployed_by: str = ""
    project_id: str
    captcha: Optional[str] = ""
    tz: Optional[str] = "Asia/Kolkata"
    portal: bool = False
    version: str | float = 1.0

    def __init__(self, **data):
        super().__init__(**data)
        self.version = self.change_version_to_float(self.version)

    @staticmethod
    def change_version_to_float(version: str | float) -> float:
        if isinstance(version, str):
            return float(version)
        return version


class ConfigurationSave(BaseModel):
    plugin_id: str
    configurations: dict = {}


class PluginListRequest(AGGridTableRequest):
    tz: str
    portal: bool = False


class EnvVar(BaseModel):
    name: str = ""
    value: str = ""


class DeployPluginRequest(BaseModel):
    app_name: str
    replicas: int = 1
    image: str
    app_id: str
    app_version: str
    env_var: Union[None, list[EnvVar]] = None
    port: int = 80


class UIDropdowns(BaseModel):
    elements: list
    portal: bool = False


class LoadConfigRequest(BaseModel):
    plugin_id: str


class ValidateCaptchaRequest(BaseModel):
    captcha: Optional[str]
    user_id: Optional[str]
    tz: Optional[str] = "Asia/Kolkata"


class DefaultResourceConfig(BaseModel):
    memory_request: str = "0"
    memory_limit: str = "1Gi"
    cpu_request: str = "10m"
    cpu_limit: str = "1"
    replicas: int = 1


class SwitchPluginState(BaseModel):
    plugin_ids: list | str = []


class DeletePlugins(BaseModel):
    plugin_ids: list | str = []


class PluginDownloadRequest(BaseModel):
    plugin_ids: list | str = []
    portal: bool = False
    version: str | float = 1.0


class GitTargetCreateUpdateSchema(BaseModel):
    git_target_id: Optional[str | None] = None
    git_target_name: str
    git_common_url: str
    git_username: str
    git_access_token: str
    created_by: str
    portal: Optional[bool] = None


class GitTargetResponseSchema(GitTargetCreateUpdateSchema):
    git_target_id: str
    git_target_name: str
    git_common_url: str
    git_username: str
    git_access_token: str


class DeleteGitTargets(BaseModel):
    target_ids: list | str = []


class GitTargetListRequest(AGGridTableRequest):
    tz: str
    portal: bool = False

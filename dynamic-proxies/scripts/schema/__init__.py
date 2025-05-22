from typing import Optional

from pydantic import BaseModel


class Envvar(BaseModel):
    name: str = ""
    value: str = ""


class ResourceAllocation(BaseModel):
    replicas: int = 1
    memory_request: str = "10Mi"
    memory_limit: str = "1024Mi"
    cpu_request: str = "10m"
    cpu_limit: str = "1000m"


class DeployConfig(BaseModel):
    app_name: str = ""
    image: str = ""
    auth: bool = False
    app_id: str = ""
    project_id: str = ""
    app_version: str = "1.0"
    env_var: list | None = None
    port: int = 8000
    gateway_proxy: Optional[str] = "/gateway"
    resources: ResourceAllocation | None = ResourceAllocation()


class StartConfig(BaseModel):
    app_name: str
    app_id: str


class StopConfig(StartConfig):
    pass


class DeleteConfig(StartConfig):
    pass


class PodStatus(BaseModel):
    app_name: str
    app_id: str
    lines: int = 10


class DeploymentStatus(BaseModel):
    plugin_list: list[str]

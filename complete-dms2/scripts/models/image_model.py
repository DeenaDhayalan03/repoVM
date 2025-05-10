from pydantic import BaseModel, ConfigDict
from typing import Optional, Union, Any, Dict, List

class ImageGithubBuildRequest(BaseModel):
    github_url: str
    dockerfile_path: Optional[str] = "Dockerfile"
    tag: Optional[str] = "default:latest"


class ImageBuildRequest(BaseModel):
    path: Optional[str] = None
    fileobj: Optional[str] = None
    tag: Optional[str] = None
    quiet: Optional[bool] = False
    nocache: Optional[bool] = False
    rm: Optional[bool] = False
    timeout: Optional[int] = None
    custom_context: Optional[bool] = False
    encoding: Optional[str] = None
    pull: Optional[bool] = False
    forcerm: Optional[bool] = False
    dockerfile: Optional[str] = None
    buildargs: Optional[Dict[str, Any]] = None
    container_limits: Optional[Dict[str, Any]] = None
    shmsize: Optional[int] = None
    labels: Optional[Dict[str, Any]] = None
    cache_from: Optional[List[str]] = None
    target: Optional[str] = None
    network_mode: Optional[str] = None
    squash: Optional[bool] = None
    extra_hosts: Optional[Union[List[str], Dict[str, str]]] = None
    platform: Optional[str] = None
    isolation: Optional[str] = None
    use_config_proxy: Optional[bool] = True
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ImageListRequest(BaseModel):
    name: Optional[str] = None
    all: Optional[bool] = False
    filters: Optional[Dict[str, Any]] = None


class ImageRemoveRequest(BaseModel):
    force: Optional[bool] = False
    noprune: Optional[bool] = False


class DockerLoginRequest(BaseModel):
    username: str
    password: str


class ImagePushRequest(BaseModel):
    local_tag: str
    remote_repo: str


class ImagePullRequest(BaseModel):
    repository: str
    local_tag: Optional[str] = None


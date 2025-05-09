from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Union, Any, Dict, List, Tuple, Literal
from datetime import datetime


class ContainerRunAdvancedRequest(BaseModel):
    image: str
    command: Optional[Union[str, List[str]]] = None
    name: Optional[str] = None
    detach: Optional[bool] = True
    auto_remove: Optional[bool] = False
    stdout: Optional[bool] = True
    stderr: Optional[bool] = False
    remove: Optional[bool] = False
    mac_address: Optional[str] = None
    mem_limit: Optional[Union[str, int]] = None
    mem_reservation: Optional[Union[str, int]] = None
    mem_swappiness: Optional[int] = None
    memswap_limit: Optional[Union[str, int]] = None
    nano_cpus: Optional[int] = None
    network: Optional[str] = None
    network_disabled: Optional[bool] = False
    network_mode: Optional[str] = None
    oom_kill_disable: Optional[bool] = False
    oom_score_adj: Optional[int] = None
    pid_mode: Optional[str] = None
    pids_limit: Optional[int] = None
    platform: Optional[str] = None
    ports: Optional[Dict[str, Union[int, List[int], Tuple[str, int], None]]] = None
    privileged: Optional[bool] = False
    publish_all_ports: Optional[bool] = False
    read_only: Optional[bool] = None
    restart_policy: Optional[Dict[str, Any]] = None
    runtime: Optional[str] = None
    security_opt: Optional[List[str]] = None
    shm_size: Optional[Union[str, int]] = None
    stdin_open: Optional[bool] = False
    stop_signal: Optional[str] = None
    storage_opt: Optional[Dict[str, Any]] = None
    stream: Optional[bool] = False
    sysctls: Optional[Dict[str, Any]] = None
    tmpfs: Optional[Dict[str, str]] = None
    tty: Optional[bool] = False
    use_config_proxy: Optional[bool] = None
    user: Optional[Union[str, int]] = None
    userns_mode: Optional[str] = None
    uts_mode: Optional[str] = None
    version: Optional[str] = None
    volume_driver: Optional[str] = None
    volumes: Optional[Dict[str, Dict[str, str]]] = None
    volumes_from: Optional[List[str]] = None
    working_dir: Optional[str] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ContainerListRequest(BaseModel):
    all: Optional[bool] = False
    before: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = -1
    since: Optional[str] = None
    sparse: Optional[bool] = False
    ignore_removed: Optional[bool] = False


class ContainerLogsRequest(BaseModel):
    stdout: Optional[bool] = True
    stderr: Optional[bool] = True
    timestamps: Optional[bool] = False
    tail: Optional[Union[int, Literal["all"]]] = "all"
    since: Optional[Union[datetime, float]] = None
    until: Optional[Union[datetime, float]] = None
    follow: Optional[bool] = False


class ContainerRemoveRequest(BaseModel):
    v: Optional[bool] = False
    link: Optional[bool] = False
    force: Optional[bool] = False


class ContainerLogsResponse(BaseModel):
    container_id: str = Field(..., title="Container ID", description="ID of the container")
    logs: List[str] = Field(..., title="Logs", description="Container logs output")
    message: Optional[str] = Field(None, title="Message", description="Status message")

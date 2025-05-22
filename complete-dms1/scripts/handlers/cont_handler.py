import docker
import json
from docker.errors import NotFound
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from scripts.utils.mongo_utils import MongoDBConnection
from scripts.models.cont_model import (
    ContainerRunAdvancedRequest,
    ContainerListRequest,
    ContainerLogsRequest,
    ContainerLogsResponse,
    ContainerRemoveRequest
)
from scripts.constants.app_constants import (
    CONTAINER_CREATE_FAILURE,
    CONTAINER_START_SUCCESS,
    CONTAINER_STOP_SUCCESS,
    CONTAINER_LIST_FAILURE,
    CONTAINER_STOP_FAILURE,
    CONTAINER_LOGS_FAILURE,
    CONTAINER_LOGS_RETRIEVED,
    CONTAINER_REMOVE_FAILURE,
    CONTAINER_REMOVE_SUCCESS,
    CONTAINER_NOT_FOUND
)
from scripts.utils.jwt_utils import get_current_user_from_token
from datetime import datetime
from scripts.logging.logger import logger
from scripts.models.jwt_model import TokenData
from scripts.utils.rate_limit_utils import check_rate_limit
from scripts.constants.api_endpoints import Endpoints
from docker.errors import DockerException


try:
    client = docker.from_env()
except Exception as e:
    print(e)
    print("Docker is not reachable")
mongo = MongoDBConnection()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/auth/login")


def run_container_advanced(data: ContainerRunAdvancedRequest, current_user: TokenData):
    try:
        kwargs = data.dict(exclude_unset=True)
        image = kwargs.pop("image")
        command = kwargs.pop("command", None)
        user_id = current_user.username

        check_rate_limit(user_id)

        for mem_field in ["mem_limit", "mem_reservation", "memswap_limit", "shm_size"]:
            if mem_field in kwargs and kwargs[mem_field] == "":
                kwargs.pop(mem_field)

        if "volumes" in kwargs:
            raw_volumes = kwargs.pop("volumes")
            cleaned_volumes = {}
            for host_path, mount_info in raw_volumes.items():
                bind = mount_info.get("bind")
                mode = mount_info.get("mode", "rw")
                if bind:
                    cleaned_volumes[host_path] = {"bind": bind, "mode": mode}
            kwargs["volumes"] = cleaned_volumes

        if "ports" in kwargs:
            ports = kwargs["ports"]
            if not any(ports.values()):
                kwargs.pop("ports")

        for k in list(kwargs.keys()):
            if kwargs[k] in ["", {}, []]:
                kwargs.pop(k)

        container = client.containers.run(image=image, command=command, **kwargs)

        containers_collection = mongo.get_collection("user_containers")
        containers_collection.insert_one({
            "user_id": user_id,
            "container_name": container.name,
            "created_time": datetime.utcnow()
        })

        return {
            "message": CONTAINER_START_SUCCESS,
            "id": container.id,
            "status": container.status
        }

    except DockerException as e:
        logger.error(f"Docker error: {e}")
        raise HTTPException(status_code=500, detail=f"{CONTAINER_CREATE_FAILURE}: {str(e)}")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        raise HTTPException(status_code=500, detail=f"{CONTAINER_CREATE_FAILURE}: {str(e)}")


def list_containers_with_filters(params: ContainerListRequest, current_user: TokenData):
    try:
        kwargs = params.dict(exclude_unset=True)

        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="You do not have permission to access all containers.")

        if "filters" in kwargs and kwargs["filters"]:
            if not isinstance(kwargs["filters"], dict):
                raise HTTPException(status_code=400, detail="Filters should be a dictionary.")
        containers = client.containers.list(**kwargs)

        return [
            {
                "name": c.name,
                "id": c.id,
                "image": c.image.tags,
                "status": c.status
            } for c in containers
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing containers: {str(e)}")


def stop_container(name: str, current_user: TokenData, timeout: float = None):
    try:
        container = client.containers.get(name)
        stop_args = {"timeout": timeout} if timeout is not None else {}

        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="You do not have permission to stop containers.")

        container.stop(**stop_args)
        return {"message": CONTAINER_STOP_SUCCESS}
    except NotFound as e:
        raise HTTPException(status_code=404, detail=f"{CONTAINER_NOT_FOUND}: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{CONTAINER_STOP_FAILURE}: {str(e)}")


def get_logs_with_params(name: str, params: ContainerLogsRequest, current_user: TokenData) -> ContainerLogsResponse:
    try:
        container = client.containers.get(name)
        opts = params.dict(exclude_unset=True)

        user_id = current_user.username

        if opts.pop("follow", False):
            raise HTTPException(status_code=400, detail="Streaming logs not supported in structured response.")

        raw_logs = container.logs(stream=False, **opts)
        logs = raw_logs.decode("utf-8", errors="ignore").splitlines()

        return ContainerLogsResponse(
            container_id=name,
            logs=logs,
            message=CONTAINER_LOGS_RETRIEVED
        )

    except NotFound:
        raise HTTPException(status_code=404, detail=CONTAINER_NOT_FOUND)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{CONTAINER_LOGS_FAILURE}: {str(e)}")

def remove_container_with_params(name: str, params: ContainerRemoveRequest, current_user: TokenData):
    try:
        container = client.containers.get(name)
        opts = params.dict(exclude_unset=True)

        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="You do not have permission to remove containers.")

        container.remove(**opts)
        return {
            "message": CONTAINER_REMOVE_SUCCESS,
            "used_options": opts
        }
    except NotFound:
        raise HTTPException(status_code=404, detail=CONTAINER_NOT_FOUND)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{CONTAINER_REMOVE_FAILURE} :{str(e)}")

from kubernetes import client, config
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime

from scripts.utils.mongo_utils import MongoDBConnection
from scripts.models.cont_model import (
    ContainerRunAdvancedRequest,
    ContainerListRequest,
    ContainerLogsRequest,
    ContainerLogsResponse,
    ContainerRemoveRequest
)
from scripts.constants.app_constants import *
from scripts.utils.jwt_utils import get_current_user_from_token
from scripts.models.jwt_model import TokenData
from scripts.utils.rate_limit_utils import check_rate_limit
from scripts.logging.logger import logger

# Configure Kubernetes client
try:
    config.load_incluster_config()
except:
    config.load_kube_config()
k8s_core = client.CoreV1Api()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/auth/login")


def create_container_advanced(data: ContainerRunAdvancedRequest, current_user: TokenData):
    try:
        check_rate_limit(current_user.username)

        pod_name = f"{data.name}-{current_user.username}"
        container = client.V1Container(
            name=pod_name,
            image=data.image,
            ports=[client.V1ContainerPort(container_port=p) for p in data.ports or []],
            env=[client.V1EnvVar(name=k, value=v) for k, v in (data.env_vars or {}).items()],
            args=data.command or None,
        )
        spec = client.V1PodSpec(containers=[container], restart_policy="Never")
        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(name=pod_name, labels={"user": current_user.username}),
            spec=spec
        )

        k8s_core.create_namespaced_pod(namespace="default", body=pod)

        with MongoDBConnection() as db:
            db.container.insert_one({
                "username": current_user.username,
                "container_name": pod_name,
                "image": data.image,
                "created_at": datetime.utcnow()
            })

        return {"message": CONTAINER_START_SUCCESS, "container_name": pod_name}
    except Exception as e:
        logger.error(f"Container creation failed: {e}")
        raise HTTPException(status_code=500, detail=CONTAINER_CREATE_FAILURE)


def stop_container(name: str, current_user: TokenData, timeout: float = None):
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="You do not have permission to stop containers.")

        k8s_core.delete_namespaced_pod(name=name, namespace="default", grace_period_seconds=int(timeout or 0))
        return {"message": CONTAINER_STOP_SUCCESS}
    except client.exceptions.ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=CONTAINER_NOT_FOUND)
        raise HTTPException(status_code=500, detail=CONTAINER_STOP_FAILURE)


def list_containers(data: ContainerListRequest, current_user: TokenData):
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="You do not have permission to access all containers.")

        pods = k8s_core.list_namespaced_pod(namespace="default")
        containers = [{"name": pod.metadata.name, "status": pod.status.phase} for pod in pods.items]
        return containers
    except Exception as e:
        logger.error(f"Failed to list containers: {e}")
        raise HTTPException(status_code=500, detail=CONTAINER_LIST_FAILURE)


def get_container_logs(data: ContainerLogsRequest, current_user: TokenData):
    try:
        if data.follow:
            raise HTTPException(status_code=400, detail="Streaming logs not supported in structured response.")

        logs = k8s_core.read_namespaced_pod_log(
            name=data.name,
            namespace="default",
            tail_lines=data.tail,
            timestamps=data.timestamps
        )
        return ContainerLogsResponse(logs=logs)
    except Exception as e:
        logger.error(f"Failed to fetch logs: {e}")
        raise HTTPException(status_code=500, detail=CONTAINER_LOGS_FAILURE)


def remove_container(data: ContainerRemoveRequest, current_user: TokenData):
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="You do not have permission to remove containers.")

        opts = data.dict(exclude_unset=True)
        k8s_core.delete_namespaced_pod(name=data.name, namespace="default", **opts)
        return {"message": CONTAINER_REMOVE_SUCCESS}
    except client.exceptions.ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=CONTAINER_NOT_FOUND)
        raise HTTPException(status_code=500, detail=CONTAINER_REMOVE_FAILURE)

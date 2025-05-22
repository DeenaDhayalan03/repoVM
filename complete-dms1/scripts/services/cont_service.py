from fastapi import APIRouter, Query, Body
from scripts.handlers.cont_handler import *
from scripts.models.cont_model import *
from scripts.constants.api_endpoints import Endpoints
from scripts.logging.logger import logger
from scripts.utils.jwt_utils import get_current_user
from scripts.models.jwt_model import TokenData

container_router = APIRouter()

@container_router.post(Endpoints.CONTAINER_CREATE_ADVANCED)
def run_container_advanced_view(
    data: ContainerRunAdvancedRequest,
    current_user: TokenData = Depends(get_current_user)
):
    try:
        logger.info(f"User '{current_user.username}' running container with advanced parameters")
        return run_container_advanced(data, current_user)
    except Exception as e:
        logger.error(f"Error running container with advanced parameters: {e}")
        raise HTTPException(status_code=500, detail="Error running container with advanced parameters")

@container_router.post(Endpoints.CONTAINER_LIST)
def list_containers_view(
    params: ContainerListRequest = Body(...),
    current_user: TokenData = Depends(get_current_user)
):
    try:
        logger.info(f"User '{current_user.username}' listing containers with filters: {params.dict(exclude_unset=True)}")
        return list_containers_with_filters(params, current_user)
    except Exception as e:
        logger.error(f"Error listing containers: {e}")
        raise HTTPException(status_code=500, detail="Error listing containers")

@container_router.post(Endpoints.CONTAINER_LOGS)
def get_container_logs(
    name: str,
    params: ContainerLogsRequest = Body(...),
    current_user: TokenData = Depends(get_current_user)
):
    try:
        logger.info(f"User '{current_user.username}' fetching logs for container '{name}' with params: {params.dict(exclude_unset=True)}")
        return get_logs_with_params(name, params, current_user)
    except Exception as e:
        logger.error(f"Error fetching logs for container '{name}': {e}")
        raise HTTPException(status_code=500, detail="Error fetching container logs")

@container_router.post(Endpoints.CONTAINER_STOP)
def stop_container_view(
    name: str,
    timeout: Optional[float] = Query(None, description="Timeout in seconds before force stop"),
    current_user: TokenData = Depends(get_current_user)
):
    try:
        logger.info(f"User '{current_user.username}' stopping container '{name}' with timeout={timeout}")
        return stop_container(name, current_user, timeout )
    except Exception as e:
        logger.error(f"Error stopping container '{name}': {e}")
        raise HTTPException(status_code=500, detail="Error stopping container")


@container_router.post(Endpoints.CONTAINER_DELETE)
def remove_container_view(
    name: str,
    params: ContainerRemoveRequest = Body(...),
    current_user: TokenData = Depends(get_current_user)
):
    try:
        logger.info(f"User '{current_user.username}' removing container '{name}' with params: {params.dict(exclude_unset=True)}")
        return remove_container_with_params(name, params, current_user)
    except Exception as e:
        logger.error(f"Error removing container '{name}': {e}")
        raise HTTPException(status_code=500, detail="Error removing container")

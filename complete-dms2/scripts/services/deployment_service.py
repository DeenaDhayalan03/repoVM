from fastapi import APIRouter, status, Depends, HTTPException
from scripts.handlers.deployment_handler import (
    list_k8s_deployments,
    create_k8s_deployment,
    delete_k8s_deployment,
    scale_k8s_deployment,
)
from scripts.models.deployment_model import DeploymentCreateRequest, DeploymentScaleRequest
from scripts.logging.logger import logger
from scripts.utils.jwt_utils import get_current_user
from scripts.models.jwt_model import TokenData
from scripts.constants.api_endpoints import Endpoints

deployment_router = APIRouter()


@deployment_router.get(Endpoints.DEPLOYMENT_LIST, status_code=status.HTTP_200_OK)
def list_deployments_view(namespace: str = "default", current_user: TokenData = Depends(get_current_user)):
    try:
        logger.info(f"Authenticated user '{current_user.username}' requested deployments in namespace '{namespace}'")
        return list_k8s_deployments(current_user, namespace)
    except Exception as e:
        logger.error(f"Error listing deployments: {e}")
        raise HTTPException(status_code=500, detail="Error listing deployments")


@deployment_router.post(Endpoints.DEPLOYMENT_CREATE, status_code=status.HTTP_201_CREATED)
def create_deployment_view(data: DeploymentCreateRequest, current_user: TokenData = Depends(get_current_user)):
    try:
        logger.info(f"Authenticated user '{current_user.username}' is creating deployment with data: {data}")
        return create_k8s_deployment(data, current_user)
    except Exception as e:
        logger.error(f"Error creating deployment: {e}")
        raise HTTPException(status_code=500, detail="Error creating deployment")


@deployment_router.patch(Endpoints.DEPLOYMENT_SCALE, status_code=status.HTTP_200_OK)
def scale_deployment_view(
    namespace: str,
    name: str,
    scale: DeploymentScaleRequest,
    current_user: TokenData = Depends(get_current_user)
):
    try:
        logger.info(f"User '{current_user.username}' requested to scale deployment '{name}' in namespace '{namespace}'")
        return scale_k8s_deployment(namespace, name, scale, current_user)
    except Exception as e:
        logger.error(f"Error scaling deployment '{name}': {e}")
        raise HTTPException(status_code=500, detail="Error scaling deployment")


@deployment_router.delete(Endpoints.DEPLOYMENT_DELETE, status_code=status.HTTP_200_OK)
def delete_deployment_view(namespace: str, name: str, current_user: TokenData = Depends(get_current_user)):
    try:
        logger.info(f"User '{current_user.username}' requested to delete deployment '{name}' in namespace '{namespace}'")
        return delete_k8s_deployment(namespace, name, current_user)
    except Exception as e:
        logger.error(f"Error deleting deployment '{name}': {e}")
        raise HTTPException(status_code=500, detail="Error deleting deployment")

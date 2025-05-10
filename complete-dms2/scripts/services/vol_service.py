from fastapi import APIRouter, status, Depends, HTTPException
from scripts.handlers.vol_handler import VolumeHandler
from scripts.models.volume_model import VolumeCreateRequest, VolumeRemoveRequest
from scripts.logging.logger import logger
from scripts.utils.jwt_utils import get_current_user
from scripts.models.jwt_model import TokenData
from scripts.constants.api_endpoints import Endpoints

volume_router = APIRouter()


@volume_router.post(Endpoints.VOLUME_CREATE, status_code=status.HTTP_201_CREATED)
def create_volume_view(data: VolumeCreateRequest, current_user: TokenData = Depends(get_current_user)):
    try:
        logger.info(
            f"User '{current_user.username}' requested to create a volume with data: {data.dict(exclude_unset=True)}"
        )
        return VolumeHandler.create_volume_with_params(data, current_user)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error creating volume: {e}")
        raise HTTPException(status_code=500, detail="Error creating volume")


@volume_router.delete(Endpoints.VOLUME_DELETE, status_code=status.HTTP_200_OK)
def remove_volume_view(name: str, params: VolumeRemoveRequest, current_user: TokenData = Depends(get_current_user)):
    try:
        logger.info(
            f"User '{current_user.username}' requested to remove volume '{name}' with options: {params.dict(exclude_unset=True)}"
        )
        return VolumeHandler.remove_volume_with_params(name, params, current_user)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error removing volume '{name}': {e}")
        raise HTTPException(status_code=500, detail="Error removing volume")

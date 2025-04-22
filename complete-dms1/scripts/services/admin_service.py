from fastapi import APIRouter, Depends, status, HTTPException
from scripts.handlers.admin_handler import (
    list_all_users,
    get_user_details,
    delete_user,
    list_all_containers
)
from scripts.constants.api_endpoints import Endpoints
from scripts.logging.logger import logger
from scripts.utils.jwt_utils import get_current_user
from scripts.models.jwt_model import TokenData

admin_router = APIRouter()

def admin_required(user: dict = Depends(get_current_user)):
    if user["role"] != "Admin":
        logger.warning(f"User '{user['username']}' attempted to access restricted route without admin privileges")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this action."
        )
    return user


@admin_router.get(Endpoints.ADMIN_USERS_LIST, status_code=status.HTTP_200_OK)
def list_users(user: dict = Depends(admin_required)):
    logger.info("Request to fetch all users")
    return list_all_users(user)


@admin_router.get(Endpoints.ADMIN_USER_DETAILS, status_code=status.HTTP_200_OK)
def get_user_info(username: str, user: dict = Depends(admin_required)):
    logger.info(f"Request to fetch details of user '{username}'")
    return get_user_details(username, user)


# @admin_router.delete(Endpoints.ADMIN_USER_DELETE, status_code=status.HTTP_200_OK)
# def delete_user_account(username: str, current_user: dict = Depends(admin_required)):
#     logger.info(f"Request to delete user '{username}'")
#     return delete_user(username, current_user)


# @admin_router.get(Endpoints.ADMIN_CONTAINERS_LIST, status_code=status.HTTP_200_OK)
# def list_containers(user: dict = Depends(admin_required)):
#     logger.info("Request to fetch all containers")
#     return list_all_containers(user)

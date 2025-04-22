from fastapi import HTTPException, status, Depends
from scripts.utils.mongo_utils import MongoDBConnection
from scripts.models.rate_limit_model import RateLimitConfig
from scripts.logging.logger import logger
from scripts.utils.jwt_utils import decode_access_token
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
from scripts.constants.api_endpoints import Endpoints


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=Endpoints.AUTH_LOGIN)

mongodb = MongoDBConnection()

def get_user_role(token: str = Depends(oauth2_scheme)) -> str:

    user_data = decode_access_token(token)
    return user_data['role']

def get_rate_limit_handler(user_id: str, role: str = Depends(get_user_role)) -> RateLimitConfig:

    if role != "Admin":
        logger.warning(f"Access denied for user '{user_id}' - Insufficient role")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role to access rate limit data"
        )

    rate_limit_collection = mongodb.get_collection("rate_limits")

    user_limit = rate_limit_collection.find_one({"user_id": user_id})
    if not user_limit:
        logger.warning(f"Rate limit not found for user '{user_id}'")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate limit configuration not found"
        )

    rate_limit_config = RateLimitConfig(
        user_id=user_limit["user_id"],
        limit=user_limit["limit"],
        time_window=user_limit["time_window"],
        reset_time=user_limit.get("reset_time"),
        remaining=user_limit.get("remaining", 0),
        last_reset=user_limit.get("last_reset"),
        created_at=user_limit.get("created_at")
    )

    logger.info(f"Fetched rate limit for user '{user_id}' successfully")
    return rate_limit_config

def set_rate_limit_handler(user_id: str, limit: int, time_window: int, role: str = Depends(get_user_role)) -> dict:

    if role != "Admin":
        logger.warning(f"Access denied for user '{user_id}' - Insufficient role")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role to set rate limit"
        )

    rate_limit_collection = mongodb.get_collection("rate_limits")

    existing = rate_limit_collection.find_one({"user_id": user_id})
    if existing:
        logger.warning(f"Attempted to set rate limit for existing user '{user_id}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rate limit already set for user"
        )

    rate_limit_collection.insert_one({
        "user_id": user_id,
        "limit": limit,
        "time_window": time_window,
        "remaining": limit,
        "last_reset": datetime.utcnow(),
        "reset_time": datetime.utcnow(),
        "created_at": datetime.utcnow()
    })

    logger.info(f"Set new rate limit for user '{user_id}' to {limit}")
    return {"message": "Rate limit set successfully"}

def update_rate_limit_handler(user_id: str, limit: int, time_window: int, role: str = Depends(get_user_role)) -> dict:

    if role != "Admin":
        logger.warning(f"Access denied for user '{user_id}' - Insufficient role")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role to update rate limit"
        )

    rate_limit_collection = mongodb.get_collection("rate_limits")

    update_result = rate_limit_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "limit": limit,
            "time_window": time_window,
            "remaining": limit,
            "reset_time": datetime.utcnow(),
            "last_reset": datetime.utcnow()
        }}
    )

    if update_result.matched_count == 0:
        logger.warning(f"Attempted to update non-existent rate limit for user '{user_id}'")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate limit configuration not found"
        )

    logger.info(f"Updated rate limit for user '{user_id}' to {limit}")
    return {"message": "Rate limit updated successfully"}

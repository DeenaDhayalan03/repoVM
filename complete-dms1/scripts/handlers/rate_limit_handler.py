from fastapi import HTTPException, status
from scripts.utils.mongo_utils import MongoDBConnection
from scripts.models.rate_limit_model import RateLimitConfig
from scripts.logging.logger import logger
from datetime import datetime
from scripts.models.jwt_model import TokenData

mongodb = MongoDBConnection()


def get_rate_limit_handler(user_id: str, current_user: TokenData) -> RateLimitConfig:
    if current_user.role != "admin":
        logger.warning(f"Access denied for user '{current_user.username}' - Insufficient role")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role to access rate limit data")

    rate_limit_collection = mongodb.get_collection("rate_limits")
    user_limit = rate_limit_collection.find_one({"user_id": user_id})
    if not user_limit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate limit configuration not found")

    return RateLimitConfig(**user_limit)


def set_rate_limit_handler(user_id: str, limit: int, time_window: int, current_user: TokenData) -> dict:
    if current_user.role != "admin":
        logger.warning(f"Access denied for user '{current_user.username}'")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role to set rate limit")

    rate_limit_collection = mongodb.get_collection("rate_limits")
    if rate_limit_collection.find_one({"user_id": user_id}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rate limit already set for user")

    now = datetime.utcnow()
    rate_limit_collection.insert_one({
        "user_id": user_id,
        "limit": limit,
        "time_window": time_window,
        "remaining": limit,
        "last_reset": now,
        "reset_time": now,
        "created_at": now
    })

    logger.info(f"Set new rate limit for user '{user_id}' to {limit}")
    return {"message": "Rate limit set successfully"}


def update_rate_limit_handler(user_id: str, limit: int, time_window: int, current_user: TokenData) -> dict:
    if current_user.role != "admin":
        logger.warning(f"Access denied for user '{current_user.username}'")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role to update rate limit")

    rate_limit_collection = mongodb.get_collection("rate_limits")
    result = rate_limit_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "limit": limit,
            "time_window": time_window,
            "remaining": limit,
            "reset_time": datetime.utcnow(),
            "last_reset": datetime.utcnow()
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate limit configuration not found")

    logger.info(f"Updated rate limit for user '{user_id}'")
    return {"message": "Rate limit updated successfully"}

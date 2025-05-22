from fastapi import HTTPException
from datetime import datetime, timedelta
from scripts.utils.mongo_utils import MongoDBConnection
from scripts.constants.app_configuration import settings
from scripts.constants.app_constants import RATE_LIMIT_EXCEEDED
from scripts.logging.logger import logger

mongo = MongoDBConnection()

MAX_CONTAINERS_PER_HOUR = settings.DEFAULT_MAX_CONTAINERS_PER_HOUR

def check_rate_limit(user_id: str) -> bool:

    try:
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        containers_collection = mongo.get_collection("user_containers")

        container_count = containers_collection.count_documents({
            "user_id": user_id,
            "created_time": {"$gte": one_hour_ago}
        })

        logger.debug(f"User {user_id} has created {container_count} containers in the last hour.")

        if container_count >= MAX_CONTAINERS_PER_HOUR:
            logger.warning(f"Rate limit exceeded for user {user_id}. Limit: {MAX_CONTAINERS_PER_HOUR} per hour.")
            raise HTTPException(
                status_code=429,
                detail=RATE_LIMIT_EXCEEDED.format(limit=MAX_CONTAINERS_PER_HOUR)
            )

        return True

    except Exception as e:
        logger.error(f"Error checking rate limit for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

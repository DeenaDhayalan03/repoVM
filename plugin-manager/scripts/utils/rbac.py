import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache, wraps

import orjson as json
from fastapi import HTTPException, Request, status
from ut_mongo_util import mongo_client

from scripts.db.mongo.catalog_meta.collections.user import User as SpaceUser
from scripts.db.mongo.catalog_meta.collections.user_space import UserSpace
from scripts.db.mongo.ilens_configurations.collections.user import User
from scripts.db.mongo.ilens_configurations.collections.user_project import UserProject
from scripts.db.redis_conn import user_role_permissions_redis


def timed_lru_cache(seconds: int = 10, maxsize: int = 128):
    def wrapper_cache(func):
        func = lru_cache(maxsize=maxsize)(func)
        func.lifetime = timedelta(seconds=seconds)
        func.expiration = datetime.now(timezone.utc) + func.lifetime

        @wraps(func)
        def wrapped_func(*args, **kwargs):
            if datetime.now(timezone.utc) >= func.expiration:
                logging.debug("Cache Expired")
                func.cache_clear()
                func.expiration = datetime.now(timezone.utc) + func.lifetime

            return func(*args, **kwargs)

        return wrapped_func

    return wrapper_cache


@timed_lru_cache(seconds=60, maxsize=1000)
def get_user_role_id_space(user_id, space_id):
    logging.debug("Fetching user role from DB")
    user_conn = SpaceUser(mongo_client=mongo_client)  # user collection from catalog_meta DB
    if user_role := user_conn.find_user_role_for_user_id(user_id=user_id, space_id=space_id):
        return user_role["userrole"][0]
    # if user not found in primary collection, check if user is in space collection
    user_space_conn = UserSpace()  # user_space collection from catalog_meta DB
    if user_role := user_space_conn.find_user_role_for_user_id(user_id=user_id, space_id=space_id):
        return user_role["userrole"][0]


@timed_lru_cache(seconds=60, maxsize=1000)
def get_user_role_id_projects(user_id, project_id):
    """"""
    logging.debug("Fetching user role from DB")
    user_conn = User()  # user collection from ilens_configuration DB
    if user_role := user_conn.find_user_by_project_id_user_role(user_id=user_id, project_id=project_id):
        return user_role["userrole"][0] if user_role.get("userrole") else None
    # if user not found in primary collection, check if user is in project collection
    user_proj_conn = UserProject()  # user_project collection from ilens_configuration DB
    if user_role := user_proj_conn.find_user_role_for_user_id(user_id=user_id, project_id=project_id):
        return user_role["userrole"][0] if user_role.get("userrole") else None


class RBAC:
    def __init__(self, entity_name: str, operation: list[str]):
        self.entity_name = entity_name
        self.operation = operation

    def check_permissions(self, user_id: str, project_id: str) -> dict[str, bool]:
        if project_id.startswith("space_"):
            user_role_id = get_user_role_id_space(user_id, project_id)
        else:
            user_role_id = get_user_role_id_projects(user_id, project_id)
        if not user_role_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User role not found!")
        r_key = f"{project_id}__{user_role_id}"  # eg: space_100__user_role_100
        user_role_rec = user_role_permissions_redis.hget(r_key, self.entity_name)
        if not user_role_rec:
            logging.error("user role not found in redis")
            return {}
        user_role_rec = json.loads(user_role_rec)
        if permission_dict := {i: True for i in self.operation if user_role_rec.get(i)}:
            return permission_dict
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient Permission!")

    def __call__(self, request: Request) -> dict[str, bool]:
        user_id = request.cookies.get("userId", request.headers.get("userId"))
        project_id = request.cookies.get("projectId", request.headers.get("projectId"))
        return self.check_permissions(user_id=user_id, project_id=project_id)

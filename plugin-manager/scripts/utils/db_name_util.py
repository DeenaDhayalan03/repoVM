import logging
from functools import lru_cache
from typing import Tuple

import ujson as json

from scripts.db.redis_conn import project_details_db


@lru_cache()
def get_db_name(project_id: str, database: str, delimiter: str = "__") -> str:
    prefix_condition, val = check_prefix_condition(project_id)
    if prefix_condition:
        # Get the prefix name from mongo or default to project_id
        prefix_name = val.get("source_meta", {}).get("prefix") or project_id
        return f"{prefix_name}{delimiter}{database}"
    return database


def check_prefix_condition(project_id: str) -> Tuple[bool, dict]:
    if not project_id:
        logging.warning("Project ID is None! Cannot check for prefix!")
        return False, {}
    redis_resp = project_details_db.get(project_id)
    if redis_resp is None:
        raise ValueError(f"Unknown Project, Project ID: {project_id} Not Found!!!")
    val: dict = json.loads(redis_resp)
    if not val:
        return False, {}

    # Get the prefix flag to apply project_id prefix to any db
    prefix_condition = bool(val.get("source_meta", {}).get("add_prefix_to_database"))
    return prefix_condition, val

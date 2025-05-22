from typing import Optional
from pydantic import BaseModel
from scripts.constants.db_constants import DatabaseConstants
from scripts.db.mongo import CollectionBaseClass, mongo_client
from scripts.db.mongo.ilens_configurations import database

collection_name = DatabaseConstants.collection_git_target


class GitTargetCollectionKeys:
    KEY_GIT_TARGET_ID = "git_target_id"
    KEY_GIT_TARGET_NAME = "git_target_name"
    KEY_GIT_COMMON_URL = "git_common_url"
    KEY_USERNAME = "git_username"
    KEY_ACCESS_TOKEN = "git_access_token"


class GitTargetSchema(BaseModel):
    git_target_id: Optional[str] = None
    git_target_name: Optional[str] = None
    git_common_url: Optional[str] = None
    git_username: Optional[str] = None
    git_access_token: Optional[str] = None
    project_id: Optional[str] = None
    created_by: Optional[str] = None
    created_on: Optional[str] = None
    updated_by: Optional[str] = None
    updated_on: Optional[str] = None
    portal: Optional[bool] = None


class GitTarget(CollectionBaseClass):
    key_git_target_id = GitTargetCollectionKeys.KEY_GIT_TARGET_ID
    key_git_target_name = GitTargetCollectionKeys.KEY_GIT_TARGET_NAME
    key_common_url = GitTargetCollectionKeys.KEY_GIT_COMMON_URL
    key_username = GitTargetCollectionKeys.KEY_USERNAME
    key_access_token = GitTargetCollectionKeys.KEY_ACCESS_TOKEN

    def __init__(self, project_id=None):
        super().__init__(
            mongo_client,
            database=database,
            collection=collection_name,
            project_id=project_id,
        )
        self.project_id = project_id

    def find_git_target(self, target_id):
        if target := self.find_one(query={self.key_git_target_id: target_id}):
            return target
        return None

    def find_git_target_by_param(self, **query):
        return GitTargetSchema(**target) if (target := self.find_one(query)) else target

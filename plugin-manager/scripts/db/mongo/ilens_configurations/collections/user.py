from typing import Dict, List, Optional

from pydantic import BaseModel

from scripts.constants.db_constants import DatabaseConstants
from scripts.db.mongo import CollectionBaseClass, mongo_client
from scripts.db.mongo.ilens_configurations import database

collection_name = DatabaseConstants.collection_user


class UserCollectionKeys:
    KEY_LANGUAGE = "language"
    KEY_NAME = "name"
    KEY_USER_ID = "user_id"
    KEY_PROJECT_ID = "project_id"
    KEY_USERNAME = "username"
    KEY_USER_ROLE = "userrole"
    KEY_EMAIL = "email"


class UserSchema(BaseModel):
    name: Optional[str] = None
    project_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    phonenumber: Optional[Dict] = None
    userrole: Optional[List[str]] = None
    user_type: Optional[str] = None
    user_id: Optional[str] = None
    AccessLevel: Optional[Dict] = None
    user_access_select_all: Optional[bool] = None
    access_group_ids: Optional[List[str]] = None
    client_id: Optional[str] = None
    created_by: Optional[str] = None
    hmi: Optional[Dict] = None
    encryption_salt: Optional[Dict] = None
    product_encrypted: Optional[bool] = None
    email_preferences: Optional[Dict] = None
    language: Optional[str] = None
    passwordReset: Optional[Dict] = None
    failed_attempts: Optional[int] = None
    is_user_locked: Optional[bool] = None
    last_failed_attempt: Optional[str] = None
    profileImage_name: Optional[str] = None
    profileImage_url: Optional[str] = None
    date_format: Optional[str] = None
    date_time_format: Optional[str] = None
    time_format: Optional[str] = None
    tz: Optional[str] = None
    app_url: Optional[str] = None
    landing_page: Optional[str] = None
    ilens_encrypted: Optional[bool] = None


class User(CollectionBaseClass):
    key_username = UserCollectionKeys.KEY_USERNAME
    key_user_id = UserCollectionKeys.KEY_USER_ID
    key_language = UserCollectionKeys.KEY_LANGUAGE
    key_name = UserCollectionKeys.KEY_NAME
    key_project_id = UserCollectionKeys.KEY_PROJECT_ID
    key_userrole = UserCollectionKeys.KEY_USER_ROLE

    def __init__(self, project_id=None):
        super().__init__(
            mongo_client,
            database=database,
            collection=collection_name,
            project_id=project_id,
        )

    def find_user(self, user_id):
        if user := self.find_one(query={self.key_user_id: user_id}):
            return user
        return None

    def find_user_by_param(self, **query):
        return UserSchema(**user) if (user := self.find_one(query)) else user

    def find_user_by_project_id(self, user_id, project_id):
        if user := self.find_one(
            query={self.key_user_id: user_id, self.key_project_id: project_id},
            filter_dict={"user_id": 1, "name": 1, "username": 1},
        ):
            return dict(user)
        else:
            return user

    def find_user_by_project_id_user_role(self, user_id, project_id):
        if user := self.find_one(query={self.key_user_id: user_id, self.key_project_id: project_id}):
            return dict(user)
        else:
            return user

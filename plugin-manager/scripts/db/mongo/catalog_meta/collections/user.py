from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from ut_mongo_util import CollectionBaseClass


class UserCollectionKeys:
    KEY_LANGUAGE = "language"
    KEY_NAME = "name"
    KEY_USER_ID = "user_id"
    KEY_SPACE_ID = "space_id"
    KEY_USERNAME = "username"
    KEY_USER_ROLE = "userrole"
    KEY_EMAIL = "email"


class UserSchema(BaseModel):
    name: Optional[str] = ""
    space_id: Optional[str] = ""
    username: Optional[str] = ""
    password: Optional[str] = ""
    email: Optional[Any] = None
    phonenumber: Optional[Any] = None
    userrole: Optional[List[str]] = None
    user_type: Optional[str] = ""
    user_id: Optional[str] = ""
    created_by: Optional[str] = ""
    encryption_salt: Optional[Dict] = {}
    passwordReset: Optional[Dict] = {}
    failed_attempts: Optional[int] = 0
    is_user_locked: Optional[bool] = False
    last_failed_login: Optional[int] = 0
    last_logged_in: Optional[int] = 0
    last_failed_attempt: Optional[str] = ""
    expires_on: Optional[str] = ""
    disable_user: Optional[bool] = False
    default_user: Optional[bool] = False
    created_on: Optional[int] = 0
    updated_by: Optional[str] = ""
    updated_on: Optional[int] = 0
    secret: Optional[str] = ""
    password_added_on: Optional[int] = 0
    default_space: Optional[str] = ""
    fixed_delay: Optional[int] = 0
    variable_delay: Optional[int] = 0


class User(CollectionBaseClass):
    def __init__(self, mongo_client):
        super().__init__(mongo_client, database="catalog_meta", collection="user")

    def find_user_role_for_user_id(self, user_id, space_id):
        query = {"user_id": user_id, "space_id": space_id}
        filter_dict = {"userrole": 1, "_id": 0}
        return self.find_one(query=query, filter_dict=filter_dict)

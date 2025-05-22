from scripts.constants.db_constants import DatabaseConstants
from scripts.db.mongo import CollectionBaseClass, mongo_client
from scripts.db.mongo.ilens_configurations import database

collection_name = DatabaseConstants.collection_user_project


class UserCollectionKeys:
    KEY_LANGUAGE = "language"
    KEY_NAME = "name"
    KEY_USER_ID = "user_id"
    KEY_PROJECT_ID = "project_id"
    KEY_USERNAME = "username"
    KEY_USER_ROLE = "userrole"


class UserProject(CollectionBaseClass):
    key_username = UserCollectionKeys.KEY_USERNAME
    key_user_id = UserCollectionKeys.KEY_USER_ID
    key_language = UserCollectionKeys.KEY_LANGUAGE
    key_name = UserCollectionKeys.KEY_NAME
    key_project_id = UserCollectionKeys.KEY_PROJECT_ID

    def __init__(self, project_id=None):
        super().__init__(
            mongo_client,
            database=database,
            collection=collection_name,
            project_id=project_id,
        )

    def fetch_user_project(self, user_id, project_id):
        return self.find_one(query={self.key_user_id: user_id, self.key_project_id: project_id})

    def fetch_user_project_with_details(self, user_id, project_id):
        query = [
            {"$match": {"user_id": user_id, "project_id": project_id}},
            {
                "$lookup": {
                    "from": "user",
                    "localField": "user_id",
                    "foreignField": "user_id",
                    "as": "user_details",
                }
            },
            {"$unwind": {"path": "$user_details"}},
            {
                "$project": {
                    "project_id": 1,
                    "user_id": 1,
                    "name": "$user_details.name",
                    "username": "$user_details.username",
                }
            },
        ]
        user = self.aggregate(query)
        return user_list[0] if (user_list := list(user)) else None

    def find_user_role_for_user_id(self, user_id, project_id):
        query = {self.key_user_id: user_id, self.key_project_id: project_id}
        filter_dict = {"userrole": 1, "_id": 0}
        return self.find_one(query=query, filter_dict=filter_dict)

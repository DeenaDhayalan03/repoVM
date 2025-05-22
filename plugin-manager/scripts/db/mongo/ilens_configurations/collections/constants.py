from scripts.constants.db_constants import DatabaseConstants
from scripts.db.mongo import CollectionBaseClass, mongo_client

from . import database

collection_name = DatabaseConstants.collection_constants


class Constants(CollectionBaseClass):
    def __init__(self):
        super().__init__(mongo_client, database=database, collection=collection_name, project_id=None)

    def get_constants_by_types(self, content_types: list):
        return self.find({"content_type": {"$in": content_types}}, filter_dict={"data": 1, "content_type": 1, "_id": 0})

    def update_constants_by_type(self, content_type: str, data: dict, update_only_if_not_exist: bool = False):
        if update_only_if_not_exist:
            return self.update_one(
                query={"content_type": content_type}, data=data, upsert=True, strategy="$setOnInsert"
            )
        return self.update_one(query={"content_type": content_type}, data=data, upsert=True)

from scripts.constants.db_constants import DatabaseConstants
from scripts.db.mongo import CollectionBaseClass, mongo_client

from . import database

collection_name = DatabaseConstants.collection_industry_category


class IndustryCategory(CollectionBaseClass):
    def __init__(self):
        super().__init__(mongo_client, database=database, collection=collection_name, project_id=None)

    def get_industry_name_by_id(self, industry_category_id: str):
        industry_name = self.find_one(
            {"industry_category_id": industry_category_id}, filter_dict={"industry_category_name": 1, "_id": 0}
        )
        if industry_name:
            return industry_name.get("industry_category_name", "NA")
        return "NA"

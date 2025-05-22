import logging

from pymongo import CursorType

from scripts.constants.db_constants import DatabaseConstants
from scripts.db.mongo import CollectionBaseClass, mongo_client

from . import db_ilens_plugin

collection_name = DatabaseConstants.collection_custom_app_plugin


class CustomAppsPlugin(CollectionBaseClass):
    def __init__(self, project_id=None):
        self.project_id = project_id
        super().__init__(
            mongo_client,
            database=db_ilens_plugin,
            collection=collection_name,
            project_id=project_id,
        )

    def create_custom_app_plugin(self, data: dict) -> str:
        resp = self.insert_one(data=data)
        return resp.inserted_id

    def update_custom_app_plugin(self, plugin_id: str, data: dict):
        resp = self.update_one(query={"plugin_id": plugin_id}, data=data, upsert=True)
        return resp.modified_count

    def update_custom_app_id(self, custom_app_pl_id: str, data: dict):
        try:
            resp = self.update_one(query={"custom_app_pl_id": custom_app_pl_id}, data=data, upsert=True)
            return resp.modified_count
        except Exception as e:
            logging.error(f"Error occurred in the update custom apps id due to {str(e)}")
            raise e

    def remove_custom_app_plugin(self, plugin_id: str) -> int:
        response = self.delete_many({"plugin_id": plugin_id})
        return response.deleted_count

    def fetch_custom_app_plugin(self, plugin_id: str) -> dict | None:
        return self.find_one(query={"plugin_id": plugin_id})

    def list_custom_app_plugin(self, skip: int, limit: int, filters: dict) -> CursorType:
        return self.find(query=filters, skip=skip, limit=limit)

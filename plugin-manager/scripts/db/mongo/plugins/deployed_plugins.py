from pymongo import CursorType

from scripts.constants.db_constants import DatabaseConstants
from scripts.db.mongo import CollectionBaseClass, mongo_client

from . import database

collection_name = DatabaseConstants.collection_deployed_plugin


class DeployedPlugins(CollectionBaseClass):
    def __init__(self, project_id=None):
        super().__init__(
            mongo_client,
            database=database,
            collection=collection_name,
            project_id=project_id,
        )

    def deploy_plugin(self, data: dict) -> str:
        resp = self.insert_one(data=data)
        return resp.inserted_id

    def update_deployment(self, deployed_plugin_id: str, data: dict):
        resp = self.update_one(query={"deployed_plugin_id": deployed_plugin_id}, data=data)
        return resp.modified_count

    def remove_deployed_plugin(self, deployed_plugin_id: str) -> int:
        response = self.delete_one({"deployed_plugin_id": deployed_plugin_id})
        return response.deleted_count

    def fetch_deployed_plugin(self, deployed_plugin_id: str) -> dict | None:
        return self.find_one(query={"deployed_plugin_id": deployed_plugin_id})

    def list_deployed_plugins(self, skip: int, limit: int, filters: dict) -> CursorType:
        return self.find(query=filters, skip=skip, limit=limit)

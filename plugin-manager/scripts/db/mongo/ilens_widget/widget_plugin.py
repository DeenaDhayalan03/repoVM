import logging

from pymongo import CursorType

from scripts.constants.db_constants import DatabaseConstants
from scripts.db.mongo import CollectionBaseClass, mongo_client

from . import db_ilens_widget

collection_name = DatabaseConstants.collection_widget_plugin


class WidgetPlugins(CollectionBaseClass):
    def __init__(self, project_id=None):
        self.project_id = project_id
        super().__init__(
            mongo_client,
            database=db_ilens_widget,
            collection=collection_name,
            project_id=project_id,
        )

    def create_widget_plugin(self, data: dict) -> str:
        resp = self.insert_one(data=data)
        return resp.inserted_id

    def update_widget_plugin(self, plugin_id: str, data: dict):
        resp = self.update_one(query={"plugin_id": plugin_id}, data=data, upsert=True)
        return resp.modified_count

    def update_widget_id(self, widget_pl_id: str, data: dict):
        try:
            resp = self.update_one(query={"widget_pl_id": widget_pl_id}, data=data, upsert=True)
            return resp.modified_count
        except Exception as e:
            logging.error(f"Error occurred in the update widget id due to {str(e)}")
            raise e

    def remove_widget_plugin(self, plugin_id: str) -> int:
        # Remove project ID from here if the widget plugin has to be deleted for all projects for non-prefixed projects
        response = self.delete_many({"plugin_id": plugin_id})
        return response.deleted_count

    def fetch_widget_plugin(self, plugin_id: str) -> dict | None:
        return self.find_one(query={"plugin_id": plugin_id})

    def list_widget_plugin(self, skip: int, limit: int, filters: dict) -> CursorType:
        return self.find(query=filters, skip=skip, limit=limit)

    def find_by_chart_type(self, chart_type, version, project_id):
        return self.find_one(query={"chart_type": chart_type, "version": version, "project_id": project_id})

    def get_aggregated_query_data(self, query):
        return self.aggregate(query)

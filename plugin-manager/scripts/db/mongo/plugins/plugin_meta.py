from pymongo.cursor import Cursor

from scripts.constants.db_constants import DatabaseConstants
from scripts.db.mongo import CollectionBaseClass, mongo_client
from scripts.db.schemas import PluginMetaDBSchema
from scripts.utils.mongo_tools.pipelines import disabeled_actions_pipeline
from scripts.utils.mongo_tools.query_buidler import AGGridMongoQueryUtil

from . import database

collection_name = DatabaseConstants.collection_plugin_meta
match_aggregation = "$match"


class PluginMeta(CollectionBaseClass):
    def __init__(self, project_id=None):
        super().__init__(
            mongo_client,
            database=database,
            collection=collection_name,
            project_id=project_id,
        )

    def create_plugin(self, plugin_id: str, data: dict, version: str = None):
        query = {"plugin_id": plugin_id}
        if version:
            query["version"] = version
        self.update_one(query=query, data=data, upsert=True)

    def update_plugin(self, plugin_id: str, data: dict, version: str = None):
        query = {"plugin_id": plugin_id}
        if "version" in data:
            del data["version"]
        if version:
            query["version"] = version
        resp = self.update_one(query=query, data=data)
        return resp.modified_count

    def get_errors(self, plugin_id: str):
        return self.find_one(query={"plugin_id": plugin_id}, filter_dict={"_id": 0, "errors": 1, "plugin_id": 1})

    def delete_plugin(self, plugin_id: str) -> int:
        response = self.delete_many({"plugin_id": plugin_id})
        return response.deleted_count

    def fetch_plugin(
        self, plugin_id: str, version: float | None = None, additional_filters: list | None = None
    ) -> PluginMetaDBSchema | None:
        query = {"plugin_id": plugin_id}
        if version is not None:
            query["version"] = version
        if additional_filters:
            query = {"$and": [query, *additional_filters]}
        data = self.find_one(query=query, filter_dict={"_id": 0})
        if not data:
            return None
        if isinstance(data["industry"], str):
            data["industry"] = [data["industry"]]
        data["status"] = data.get("status")
        return PluginMetaDBSchema(**data)

    def fetch_plugin_for_start_stop(
        self, plugin_id: str, version: float | None = None, additional_filters: list | None = None
    ) -> PluginMetaDBSchema | None:
        query = {"plugin_id": plugin_id}
        if version is not None:
            query["current_version"] = version
        if additional_filters:
            query = {"$and": [query, *additional_filters]}
        data = self.find_one(query=query, filter_dict={"_id": 0})
        if data and "current_version" in data:
            data["version"] = data.get("current_version")
            deployment_status_data = self.find_one(
                query={"plugin_id": plugin_id, "version": data["current_version"]},
                filter_dict={"_id": 0, "deployment_status": 1},
            )
            if deployment_status_data:
                data["deployment_status"] = deployment_status_data.get("deployment_status")
        if not data:
            return None
        if isinstance(data["industry"], str):
            data["industry"] = [data["industry"]]
        data["status"] = data.get("status")
        return PluginMetaDBSchema(**data)

    def list_plugins(
        self, skip: int, limit: int, filters: dict | None = None, required_fields: dict | None = None
    ) -> Cursor:
        required_fields["_id"] = 0
        return self.find(query=filters or {}, skip=skip, limit=limit, filter_dict=required_fields)

    def list_plugin_ag_grid(self, list_request, *, additional_projection: dict | None = None):
        query_builder = AGGridMongoQueryUtil()
        sort_stage = {"$sort": {"deployed_on": -1}}
        query_builder.aggregation_pipeline = [disabeled_actions_pipeline, sort_stage]
        if additional_projection is None:
            additional_projection = {}
        additional_projection["current_version"] = 1
        query = query_builder.build_query(list_request, additional_projection=additional_projection)
        query.insert(0, self.get_portal_condition(portal=list_request.portal))
        query.insert(1, {"$addFields": {"current_version": {"$ifNull": ["$current_version", "$version"]}}})
        query.insert(2, {match_aggregation: {"$expr": {"$eq": ["$current_version", "$version"]}}})
        return self.aggregate(query)

    @staticmethod
    def get_portal_condition(portal: bool) -> dict:
        if portal:
            return {match_aggregation: {"portal": portal}}
        else:
            return {match_aggregation: {"$or": [{"portal": portal}, {"portal": {"$exists": False}}]}}

    def get_counts_ag_grid(self, list_request):
        query_builder = AGGridMongoQueryUtil()
        query = query_builder.build_query(list_request)
        query.insert(0, self.get_portal_condition(portal=list_request.portal))
        new_query = [each_stage for each_stage in query if "$skip" not in each_stage and "$limit" not in each_stage]
        new_query.append({"$group": {"_id": "$plugin_id"}})
        new_query.append({"$count": "count"})
        count_data = list(self.aggregate(new_query))
        if count_data and isinstance(count_data[0], dict):
            return count_data[0].get("count")
        return 0

    def get_all_count(self, filters: dict | None = None):
        return self.count_documents(filters)

    def get_plugins_dict(self, plugin_id_list):
        data = self.find(query={"plugin_id": {"$in": plugin_id_list}, "status": "running"})
        return {x["plugin_id"]: x for x in data}

    def fetch_by_git_target(self, git_target_id: str):
        return self.find_one(query={"git_target_id": git_target_id}, filter_dict={"_id": 0, "plugin_id": 1})

    def fetch_plugin_versions(self, plugin_id: str) -> list:
        cursor = self.find(query={"plugin_id": plugin_id}, filter_dict={"_id": 0, "version": 1})
        return [doc["version"] for doc in cursor if "version" in doc]

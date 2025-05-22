from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
from scripts.services.v1.schemas import (
    GitTargetResponseSchema,
    GitTargetCreateUpdateSchema,
    GitTargetListRequest,
)
from scripts.db.mongo.ilens_configurations.collections.git_target import GitTarget
from scripts.utils.mongo_tools.query_builder_git_targets import NewQueryBuilder
from scripts.constants.ui_components import (
    git_target_list_table_actions,
    git_target_list_table_column_defs,
)
from scripts.utils.git_tools import verify_git_credentials
from scripts.constants import git_access_token_mask
from ut_security_util import MetaInfoSchema
from scripts.db import PluginMeta
import traceback


GIT_TARGET_NOT_FOUND_MSG = "Git target not found"


class GitTargetHandler:
    def __init__(self, project_id: Optional[str] = None):
        self.git_target = GitTarget(project_id=project_id)
        self.project_id = project_id
        self.plugin_db_conn = PluginMeta(project_id=self.project_id)
        self.key_mapping = {
            "targetId": "git_target_id",
            "targetName": "git_target_name",
            "createdOn": "created_on",
            "createdBy": "created_by",
            "username": "git_username",
            "url": "git_common_url",
            "access_token": "git_access_token",
        }

    def save_git_target(
        self, target_id: Optional[str], data: GitTargetCreateUpdateSchema, user_details: MetaInfoSchema
    ) -> GitTargetResponseSchema:
        new_target_data = data.model_dump()
        current_time = datetime.now(timezone.utc)
        collection_keys = self.git_target
        _ = user_details

        if target_id:
            self._validate_target_id(target_id)
            existing_target = self.git_target.find_git_target(target_id)
            if not existing_target:
                raise HTTPException(status_code=404, detail=GIT_TARGET_NOT_FOUND_MSG)

            new_target_data[collection_keys.key_git_target_id] = target_id
            new_target_data["updated_by"] = data.created_by
            new_target_data["updated_on"] = current_time
        else:
            if self._is_name_duplicate(new_target_data[collection_keys.key_git_target_name]):
                raise HTTPException(
                    status_code=400,
                    detail=f"A git target with the name {new_target_data[collection_keys.key_git_target_name]} already exists.",
                )

            new_target_data[collection_keys.key_git_target_id] = str(ObjectId())
            new_target_data["created_by"] = data.created_by
            new_target_data["created_on"] = current_time
        new_target_data = {k: v for k, v in new_target_data.items() if not k.startswith("$")}
        if new_target_data.get("git_access_token") == git_access_token_mask:
            del new_target_data["git_access_token"]

        new_target_data["portal"] = data.portal if data.portal is not None else False

        self._upsert_git_target(
            query={collection_keys.key_git_target_id: new_target_data[collection_keys.key_git_target_id]},
            data=new_target_data,
        )
        return GitTargetResponseSchema(**new_target_data)

    def _validate_target_id(self, target_id: str):
        """Validate if the target ID format is correct."""
        if not ObjectId.is_valid(target_id):
            raise HTTPException(status_code=400, detail="Invalid target_id format")

    def _is_name_duplicate(self, git_target_name: str, exclude_id: Optional[str] = None) -> bool:
        """Check if a git target name is already taken."""
        query = {self.git_target.key_git_target_name: git_target_name}
        if exclude_id:
            query["_id"] = {"$ne": ObjectId(exclude_id)}
        return self.git_target.find_one(query) is not None

    def _upsert_git_target(self, query: dict, data: dict):
        """Perform an upsert operation to save or update a Git target."""
        data = {k: v for k, v in data.items() if not k.startswith("$")}
        self.git_target.update_one(query, data, upsert=True)

    def list_git_targets(self, list_request: GitTargetListRequest) -> dict:
        """
        List Git targets with filtering, sorting, and pagination.
        """
        required_fields = {
            "git_target_name": 1,
            "created_on": 1,
            "created_by": 1,
            "git_target_id": 1,
            "git_username": 1,
            "git_common_url": 1,
            "git_access_token": 1,
            "portal": 1,
            "_id": 0,
        }

        query_builder = NewQueryBuilder()
        query_builder.project(required_fields)
        filters = list_request.filters.filter_model or {}
        filter_conditions = []

        for field, filter_data in filters.items():
            if "filter" in filter_data:
                db_field = self.key_mapping.get(field, field)
                filter_conditions.append(self.build_column_query(filter_data, db_field))

        query_builder.match(filter_conditions)
        sort_model = list_request.filters.sort_model or []
        query_builder.sort(sort_model, self.key_mapping)
        skip = list_request.start_row
        limit = list_request.records
        query_builder.paginate(skip, limit)
        query_pipeline = query_builder.build()
        git_targets = list(self.git_target.aggregate(query_pipeline))
        body_content = [
            {
                "targetId": record["git_target_id"],
                "targetName": record["git_target_name"],
                "createdOn": record["created_on"].strftime("%d %b %Y"),
                "createdBy": record["created_by"],
                "username": record["git_username"],
                "url": record["git_common_url"],
                "access_token": "*" * len(record["git_access_token"]) if "git_access_token" in record else None,
                "portal": record.get("portal", False),
            }
            for record in git_targets
        ]
        count_query = [{"$match": {"$and": filter_conditions}}] if filter_conditions else []
        total_no_cursor = list(self.git_target.aggregate(count_query + [{"$count": "count"}]))
        total_count = total_no_cursor[0]["count"] if total_no_cursor else 0
        end_of_records = (skip + limit) >= total_count
        return {
            "bodyContent": body_content,
            "total_no": total_count,
            "endOfRecords": end_of_records,
        }

    def list_portal_git_targets(self, list_request: GitTargetListRequest) -> dict:
        required_fields = {
            "git_target_name": 1,
            "created_on": 1,
            "created_by": 1,
            "git_target_id": 1,
            "git_username": 1,
            "git_common_url": 1,
            "git_access_token": 1,
            "portal": 1,
            "_id": 0,
        }

        query_builder = NewQueryBuilder()
        query_builder.project(required_fields)
        filters = list_request.filters.filter_model or {}
        filter_conditions = [{"portal": True}]  # Only list Git targets with portal set to True

        for field, filter_data in filters.items():
            if "filter" in filter_data:
                db_field = self.key_mapping.get(field, field)
                filter_conditions.append(self.build_column_query(filter_data, db_field))

        query_builder.match(filter_conditions)
        sort_model = list_request.filters.sort_model or []
        query_builder.sort(sort_model, self.key_mapping)
        skip = list_request.start_row
        limit = list_request.records
        query_builder.paginate(skip, limit)
        query_pipeline = query_builder.build()
        git_targets = list(self.git_target.aggregate(query_pipeline))
        body_content = [
            {
                "targetId": record["git_target_id"],
                "targetName": record["git_target_name"],
                "createdOn": record["created_on"].strftime("%d %b %Y"),
                "createdBy": record["created_by"],
                "username": record["git_username"],
                "url": record["git_common_url"],
                "access_token": "*" * len(record["git_access_token"]) if "git_access_token" in record else None,
                "portal": record.get("portal", False),
            }
            for record in git_targets
        ]
        count_query = [{"$match": {"$and": filter_conditions}}] if filter_conditions else []
        total_no_cursor = list(self.git_target.aggregate(count_query + [{"$count": "count"}]))
        total_count = total_no_cursor[0]["count"] if total_no_cursor else 0
        end_of_records = (skip + limit) >= total_count
        return {
            "bodyContent": body_content,
            "total_no": total_count,
            "endOfRecords": end_of_records,
        }

    def build_column_query(self, filter_obj, column):
        """
        Build individual column queries for filtering.
        """
        filter_type = filter_obj.get("filterType")
        filter_value = filter_obj.get("filter")

        if filter_type == "text":
            return {column: {"$regex": filter_value, "$options": "i"}}
        elif filter_type == "number":
            return {column: filter_value}
        elif filter_type == "date":
            return {column: {"$eq": filter_value}}
        else:
            raise ValueError(f"Unsupported filter type: {filter_type}")

    def get_git_target(self, git_target_id: str):
        """
        Retrieve information about a specific Git target by its ID.
        """
        try:
            git_target = self.git_target.find_git_target(git_target_id)
            if not git_target:
                raise HTTPException(status_code=404, detail=GIT_TARGET_NOT_FOUND_MSG)
            if "git_access_token" in git_target:
                git_target["git_access_token"] = "*" * len(git_target["git_access_token"])
            return git_target
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to retrieve git target")

    def delete_git_target(self, target_id: str) -> bool:
        """Delete a Git target by its ID."""
        self._validate_target_id(target_id)

        git_target = self.git_target.find_git_target(target_id)
        if not git_target:
            raise HTTPException(status_code=404, detail=GIT_TARGET_NOT_FOUND_MSG)

        if self.plugin_db_conn.fetch_by_git_target(target_id):
            raise HTTPException(
                status_code=400,
                detail="This Git target cannot be deleted because it is associated with existing plugins. Please delete all related plugins before attempting to delete this Git target.",
            )
        result = self.delete_gittarget({self.git_target.key_git_target_id: target_id})
        if result == 0:
            raise HTTPException(status_code=500, detail="Failed to delete git target")

        return True

    def delete_gittarget(self, filter: dict) -> int:
        response = self.git_target.delete_one(filter)
        return response.deleted_count

    def git_validation(
        self,
        target: GitTargetCreateUpdateSchema,
    ):
        """
        Single function to validate GitLab token, username, and fetch all projects under a group.
        """
        try:

            return verify_git_credentials(target.git_username, target.git_access_token, target.git_common_url)

        except Exception as e:
            error_message = f"Unexpected error: {e}"
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=error_message)

    def git_headercontent(self):
        """
        Combine the table column definitions and actions with additional metadata.
        """
        return {
            "updateColDefs": False,
            "columnDefs": git_target_list_table_column_defs,
            "rowModelType": "infinite",
            "actions": git_target_list_table_actions["actions"],
            "externalActions": git_target_list_table_actions["externalActions"],
            "endOfRecords": False,
        }

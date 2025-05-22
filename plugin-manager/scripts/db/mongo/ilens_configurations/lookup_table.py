import logging
from typing import List, Optional

from pydantic import BaseModel

from scripts.constants.db_constants import DatabaseConstants, LookupKeys
from scripts.db.mongo import CollectionBaseClass, mongo_client
from scripts.db.mongo.ilens_configurations import database

collection_name = DatabaseConstants.collection_lookup


class LookupSchema(BaseModel):
    lookup_name: Optional[str]
    description: Optional[str]
    lookup_id: str
    lookup_data: Optional[List]
    project_id: Optional[str]


class Lookups(CollectionBaseClass):
    def __init__(self, project_id=None):
        super().__init__(
            mongo_client,
            database=database,
            collection=collection_name,
            project_id=project_id,
        )
        self.project_id = project_id

    @property
    def key_lookup_id(self):
        return LookupKeys.KEY_ID

    @property
    def key_name(self):
        return LookupKeys.KEY_NAME

    def find_all_lookups(self, **query):
        """
        The following function will give all lookups for the given set of
        search parameters as keyword arguments
        :return:
        """
        all_lookups = self.find(query)
        return list(all_lookups) if all_lookups else []

    def find_by_id(self, lookup_id):
        """
        The following function will give one lookup for a given set of
        search parameters as keyword arguments
        :return:
        """
        return self.find_one(query={self.key_lookup_id: lookup_id})

    def find_one_lookup(self, lookup_name, project_id, filter_dict=None):
        query = {self.key_name: lookup_name, "project_id": project_id}
        record = self.find_one(query=query, filter_dict=filter_dict)
        return dict(record) if record else {}

    def find_one_lookup_name(self, lookup_name, filter_dict=None):
        query = {self.key_name: lookup_name}
        record = self.find_one(query=query, filter_dict=filter_dict)
        return dict(record) if record else {}

    def find_by_param(self, **query):
        """
        The following function will give one lookup for a given set of
        search parameters as keyword arguments
        :return:
        """
        return list(one_lookup) if (one_lookup := self.find(query)) else []

    def update_one_lookup(self, lookup_id, data):
        """
        The following function will update one lookup in
        tags collection based on the given query
        """
        query_dict = {self.key_lookup_id: lookup_id}
        return self.update_one(data=data, query=query_dict)

    def insert_one_lookup(self, data):
        return self.insert_one(data)

    def delete_one_lookup(self, lookup_id):
        """
        The following function will delete one lookup in
        tags collection based on the given query
        """
        if lookup_id:
            return self.delete_one(query={self.key_lookup_id: lookup_id})
        else:
            return False

    def find_by_aggregate(self, query):
        return list(record) if (record := self.aggregate(query)) else []

    def map_lookup_keys(self, lookup_name, project_id):
        query = {self.key_name: lookup_name, "project_id": project_id}
        _record = self.find_one(query=query)
        return {record["lookupdata_id"]: record["lookup_value"] for record in _record["lookup_data"]} if _record else {}

    def find_one_and_update(self, query, data, upsert=True):
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            response = collection.update_one(query, data, upsert=upsert)
            return response.modified_count
        except Exception as e:
            logging.error(str(e))
            raise

    def find_one_lookup_as_label_value(self, lookup_name, project_id, filter_dict=None):
        query = {self.key_name: lookup_name, "project_id": project_id}
        record = self.find_one(query=query, filter_dict=filter_dict)
        label_value_list = []
        if record:
            label_value_list.extend(
                {
                    "label": each_lookup.get("lookup_value"),
                    "value": each_lookup.get("lookupdata_id"),
                }
                for each_lookup in record.get("lookup_data", [])
            )
        return label_value_list

    def get_lookup_property_values(self, lookup_name, project_id, property, lookup_id_list, filter_dict=None):
        create_property_dict = {}
        query = {self.key_name: lookup_name, "project_id": project_id}
        if record := self.find_one(query=query, filter_dict=filter_dict):
            for each_lookup in record.get("lookup_data", []):
                if lookup_id_list and each_lookup["lookupdata_id"] not in lookup_id_list:
                    continue
                for each_property in each_lookup["properties"]:
                    if each_property["key"] == property:
                        create_property_dict[each_lookup["lookupdata_id"]] = each_property["value"]
                        break
        return create_property_dict

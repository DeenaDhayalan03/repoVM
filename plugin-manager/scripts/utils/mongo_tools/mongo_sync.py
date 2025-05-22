import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from pymongo import MongoClient
from pymongo.command_cursor import CommandCursor
from pymongo.cursor import Cursor
from pymongo.results import (
    DeleteResult,
    InsertManyResult,
    InsertOneResult,
    UpdateResult,
)

from ..db_name_util import get_db_name

META_SOFT_DEL: bool = os.getenv("META_SOFT_DEL", True)


class MongoCollectionBaseClass:
    def __init__(
        self,
        mongo_client: MongoClient,
        database: str,
        collection: str,
        project_id: Optional[str],
        soft_delete: bool = META_SOFT_DEL,
    ) -> None:
        self.client = mongo_client
        self.database = database
        self.collection = collection
        self.soft_delete = soft_delete
        if project_id:
            self.database = get_db_name(project_id=project_id, database=self.database)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(database={self.database}, collection={self.collection})"

    def insert_one(self, data: Dict) -> InsertOneResult:
        """
        The function is used to inserting a document to a collection in a Mongo Database.
        :param data: Data to be inserted
        :return: Insert ID
        """
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            return collection.insert_one(data)
        except Exception as e:
            logging.exception(e)
            raise

    def insert_many(self, data: List) -> InsertManyResult:
        """
        The function is used to inserting documents to a collection in a Mongo Database.
        :param data: List of Data to be inserted
        :return: Insert IDs
        """
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            return collection.insert_many(data)
        except Exception as e:
            logging.exception(e)
            raise

    def find(
        self,
        query: dict,
        filter_dict: Optional[dict] = None,
        sort: Union[None, str, Sequence[Tuple[str, Union[int, str, Mapping[str, Any]]]]] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> Cursor:
        """
        The function is used to query documents from a given collection in a Mongo Database
        :param query: Query Dictionary
        :param filter_dict: Filter Dictionary
        :param sort: List of tuple with key and direction. [(key, -1), ...]
        :param skip: Skip Number
        :param limit: Limit Number
        :return: List of Documents
        """
        if sort is None:
            sort = []
        if filter_dict is None:
            filter_dict = {"_id": 0}
        database_name = self.database
        collection_name = self.collection
        try:
            db = self.client[database_name]
            collection = db[collection_name]
            if len(sort) > 0:
                cursor = (
                    collection.find(
                        query,
                        filter_dict,
                    )
                    .sort(sort)
                    .skip(skip)
                )
            else:
                cursor = collection.find(
                    query,
                    filter_dict,
                ).skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            return cursor
        except Exception as e:
            logging.exception(e)
            raise

    def find_one(self, query: dict, filter_dict: Optional[dict] = None) -> dict | None:
        try:
            database_name = self.database
            collection_name = self.collection
            if filter_dict is None:
                filter_dict = {"_id": 0}
            db = self.client[database_name]
            collection = db[collection_name]
            return collection.find_one(query, filter_dict)
        except Exception as e:
            logging.exception(e)
            raise

    def update_one(
        self,
        query: dict,
        data: dict,
        upsert: bool = False,
        strategy: str = "$set",
    ) -> UpdateResult:
        """

        :param strategy:
        :param upsert:
        :param query:
        :param data:
        :return:
        """
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            return collection.update_one(query, {strategy: data}, upsert=upsert)
        except Exception as e:
            logging.exception(e)
            raise

    def update_many(self, query: dict, data: dict, upsert: bool = False) -> UpdateResult:
        """

        :param upsert:
        :param query:
        :param data:
        :return:
        """
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            return collection.update_many(query, {"$set": data}, upsert=upsert)
        except Exception as e:
            logging.exception(e)
            raise

    def delete_many(self, query: dict) -> DeleteResult:
        """
        :param query:
        :return:
        """
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            if self.soft_delete:
                soft_del_query = [
                    {"$match": query},
                    {"$addFields": {"deleted": {"on": datetime.now().replace(tzinfo=timezone.utc)}}},
                    {
                        "$merge": {
                            "into": {"db": f"deleted__{database_name}", "coll": collection_name},
                        }
                    },
                ]
                collection.aggregate(soft_del_query)
            return collection.delete_many(query)
        except Exception as e:
            logging.exception(e)
            raise

    def delete_one(self, query: dict) -> DeleteResult:
        """
        :param query:
        :return:
        """
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            if self.soft_delete:
                soft_del_query = [
                    {"$match": query},
                    {"$addFields": {"deleted": {"on": datetime.now().replace(tzinfo=timezone.utc)}}},
                    {
                        "$merge": {
                            "into": {"db": f"deleted__{database_name}", "coll": collection_name},
                        }
                    },
                ]
                collection.aggregate(soft_del_query)
            return collection.delete_one(query)
        except Exception as e:
            logging.exception(e)
            raise

    def count_documents(self, query: dict | None = None):
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            return collection.count_documents(query or {})
        except Exception as e:
            logging.exception(e)
            raise

    def distinct(self, query_key: str, filter_json: Optional[dict] = None) -> list:
        """
        :param query_key:
        :param filter_json:
        :return:
        """
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            return collection.distinct(query_key, filter_json)
        except Exception as e:
            logging.exception(e)
            raise

    def aggregate(
        self,
        pipelines: list,
    ) -> CommandCursor:
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            return collection.aggregate(pipelines)
        except Exception as e:
            logging.exception(e)
            raise

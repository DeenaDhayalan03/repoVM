"""
Mongo Utility
Author: Irfanuddin Shafi Ahmed
Reference: Pymongo Documentation
"""

from typing import Dict, List, Optional

from pymongo import MongoClient
from pymongo.cursor import Cursor

from scripts.logging import logger


class MongoConnect:
    def __init__(self, uri):
        try:
            self.uri = uri
            self.client = MongoClient(self.uri, connect=False)
        except Exception as e:
            logger.error(f"Exception in connection {(str(e))}")
            raise e

    def __call__(self, *args, **kwargs):
        return self.client

    def __repr__(self):
        return f"Mongo Client(uri:{self.uri}, server_info={self.client.server_info()})"


class MongoCollectionBaseClass:
    def __init__(self, mongo_client, database, collection):
        self.client = mongo_client
        self.database = database
        self.collection = collection

    def __repr__(self):
        return f"{self.__class__.__name__}(database={self.database}, collection={self.collection})"

    def insert_one(self, data: Dict):
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
            response = collection.insert_one(data)
            return response.inserted_id
        except Exception as e:
            logger.error(f"Error in inserting the data {str(e)}")
            raise e

    def insert_many(self, data: List):
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
            response = collection.insert_many(data)
            return response.inserted_ids
        except Exception as e:
            logger.error(f"Failed to insert many details {str(e)}")
            raise e

    def find(
        self,
        query: Dict,
        filter_dict: Optional[Dict] = None,
        sort=None,
        skip: Optional[int] = 0,
        collation: Optional[bool] = False,
        limit: Optional[int] = None,
    ) -> Cursor:
        """
        The function is used to query documents from a given collection in a Mongo Database
        :param query: Query Dictionary
        :param filter_dict: Filter Dictionary
        :param sort: List of tuple with key and direction. [(key, -1), ...]
        :param skip: Skip Number
        :param limit: Limit Number
        :param collation:
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
            if collation:
                cursor = cursor.collation({"locale": "en"})

            return cursor
        except Exception as e:
            logger.error(f"Error in fetching {str(e)}")
            raise e

    def find_one(self, query: Dict, filter_dict: Optional[Dict] = None):
        try:
            database_name = self.database
            collection_name = self.collection
            if filter_dict is None:
                filter_dict = {"_id": 0}
            db = self.client[database_name]
            collection = db[collection_name]
            return collection.find_one(query, filter_dict)
        except Exception as e:
            logger.error(f"Failed to fetch {str(e)}")
            raise e

    def find_decrypted(self, query: Dict, filter_dict: Optional[Dict] = None):
        try:
            database_name = self.database
            collection_name = self.collection
            if filter_dict is None:
                filter_dict = {"_id": 0}
            db = self.client[database_name]
            collection = db[collection_name]
            mongo_response = collection.find_one(query, filter_dict)
            if mongo_response:
                mongo_response = [mongo_response]
                mongo_response = self.fetch_records_from_object(body=mongo_response)
                response = mongo_response[0]
                return response
            else:
                return mongo_response
        except Exception as e:
            logger.error(f"Failed to find decrypted {str(e)}")
            raise e

    def update_one(
        self,
        query: Dict,
        data: Dict,
        upsert: bool = False,
    ):
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
            response = collection.update_one(query, {"$set": data}, upsert=upsert)
            return response.modified_count
        except Exception as e:
            logger.error(f"Failed to update one doc {str(e)}")
            raise e

    def update_many(self, query: Dict, data: Dict, upsert: bool = False):
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
            response = collection.update_many(query, {"$set": data}, upsert=upsert)
            return response.modified_count
        except Exception as e:
            logger.error(f"Failed to update many {str(e)}")
            raise e

    def delete_many(self, query: Dict):
        """
        :param query:
        :return:
        """
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            response = collection.delete_many(query)
            return response.deleted_count
        except Exception as e:
            logger.error(f"Failed to delete {str(e)}")
            raise e

    def delete_one(self, query: Dict):
        """
        :param query:
        :return:
        """
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            response = collection.delete_one(query)
            return response.deleted_count
        except Exception as e:
            logger.error(f"Failed to delete {str(e)}")
            raise e

    def distinct(self, query_key: str, filter_json: Optional[Dict] = None):
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
            logger.error(f"Failed to distinct {str(e)}")
            raise e

    def aggregate(self, pipelines: List, allow_disk_use: Optional[bool] = False):
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            return collection.aggregate(pipelines, allowDiskUse=allow_disk_use)
        except Exception as e:
            logger.error(f"Failed to aggregate {str(e)}")
            raise e

    def find_count(self, json_data, database_name, collection_name):
        """

        :param json_data:
        :param database_name: The database to which the collection/ documents belongs to.
        :param collection_name: The collection to which the documents belongs to.
        :return:
        """
        try:
            db = self.client[database_name]
            return db[collection_name].find(json_data).count()
        except Exception as e:
            logger.error(f"Failed to find count {str(e)}")
            raise e

    def count_documents(self, query: Dict):
        """
        :param query:
        :return:
        """
        try:
            database_name = self.database
            collection_name = self.collection
            db = self.client[database_name]
            collection = db[collection_name]
            return collection.count_documents(query)
        except Exception as e:
            logger.error(f"Failed to count documents {str(e)}")
            raise e

    def bulk_write(self, operation):
        try:
            database_name = self.database
            collection_name = self.collection
            database_connection = self.client[database_name]
            database_connection[collection_name].bulk_write(operation)
            return "success"
        except Exception as e:
            logger.error(f"Failed to bulk write {str(e)}")
            raise e


class MongoAggregateBaseClass:
    def __init__(
        self,
        mongo_client,
        database,
    ):
        self.client = mongo_client
        self.database = database

    def aggregate(
        self,
        collection,
        pipelines: List,
    ):
        try:
            database_name = self.database
            collection_name = collection
            db = self.client[database_name]
            collection = db[collection_name]
            return collection.aggregate(pipelines)
        except Exception as e:
            logger.error(f"Failed to get the aggregate data {str(e)}")
            raise e

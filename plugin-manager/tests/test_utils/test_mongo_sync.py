import pytest
from unittest.mock import patch, MagicMock
from pymongo.results import InsertOneResult, InsertManyResult, UpdateResult, DeleteResult
from scripts.utils.mongo_tools.mongo_sync import MongoCollectionBaseClass


@pytest.fixture
def mongo_client():
    return MagicMock()


@pytest.fixture
def mongo_collection(mongo_client):
    return MongoCollectionBaseClass(mongo_client, "test_db", "test_collection", "project_139")


def test_inserts_single_document_successfully(mongo_collection):
    data = {"key": "value"}
    with patch.object(
        mongo_collection.client[mongo_collection.database][mongo_collection.collection],
        "insert_one",
        return_value=InsertOneResult({"inserted_id": "1234"}, True),
    ) as mock_insert:
        result = mongo_collection.insert_one(data)
        assert result.inserted_id == {"inserted_id": "1234"}
        mock_insert.assert_called_once_with(data)


def test_inserts_multiple_documents_successfully(mongo_collection):
    data = [{"key": "value1"}, {"key": "value2"}]
    with patch.object(
        mongo_collection.client[mongo_collection.database][mongo_collection.collection],
        "insert_many",
        return_value=InsertManyResult({"inserted_ids": ["1234", "5678"]}, True),
    ) as mock_insert:
        result = mongo_collection.insert_many(data)
        assert result.inserted_ids == {"inserted_ids": ["1234", "5678"]}
        mock_insert.assert_called_once_with(data)


def test_finds_documents_with_query(mongo_collection):
    query = {"key": "value"}
    with patch.object(
        mongo_collection.client[mongo_collection.database][mongo_collection.collection],
        "find",
        return_value=MagicMock(),
    ) as mock_find:
        result = mongo_collection.find(query)
        assert result is not None
        mock_find.assert_called_once_with(query, {"_id": 0})


def test_finds_single_document_with_query(mongo_collection):
    query = {"key": "value"}
    with patch.object(
        mongo_collection.client[mongo_collection.database][mongo_collection.collection],
        "find_one",
        return_value={"key": "value"},
    ) as mock_find_one:
        result = mongo_collection.find_one(query)
        assert result == {"key": "value"}
        mock_find_one.assert_called_once_with(query, {"_id": 0})


def test_updates_single_document_successfully(mongo_collection):
    query = {"key": "value"}
    data = {"key": "new_value"}
    with patch.object(
        mongo_collection.client[mongo_collection.database][mongo_collection.collection],
        "update_one",
        return_value=UpdateResult({"n": 1, "nModified": 1, "ok": 1}, True),
    ) as mock_update:
        result = mongo_collection.update_one(query, data)
        assert result.matched_count == 1
        assert result.modified_count == 1
        mock_update.assert_called_once_with(query, {"$set": data}, upsert=False)


def test_deletes_multiple_documents_successfully(mongo_collection):
    query = {"key": "value"}
    with patch.object(
        mongo_collection.client[mongo_collection.database][mongo_collection.collection],
        "delete_many",
        return_value=DeleteResult({"n": 2, "ok": 1}, True),
    ) as mock_delete:
        result = mongo_collection.delete_many(query)
        assert result.deleted_count == 2
        mock_delete.assert_called_once_with(query)


def test_counts_documents_successfully(mongo_collection):
    query = {"key": "value"}
    with patch.object(
        mongo_collection.client[mongo_collection.database][mongo_collection.collection],
        "count_documents",
        return_value=5,
    ) as mock_count:
        result = mongo_collection.count_documents(query)
        assert result == 5
        mock_count.assert_called_once_with(query)


def test_retrieves_distinct_values(mongo_collection):
    query_key = "key"
    with patch.object(
        mongo_collection.client[mongo_collection.database][mongo_collection.collection],
        "distinct",
        return_value=["value1", "value2"],
    ) as mock_distinct:
        result = mongo_collection.distinct(query_key)
        assert result == ["value1", "value2"]
        mock_distinct.assert_called_once_with(query_key, None)


def test_aggregates_documents_successfully(mongo_collection):
    pipelines = [{"$match": {"key": "value"}}]
    with patch.object(
        mongo_collection.client[mongo_collection.database][mongo_collection.collection],
        "aggregate",
        return_value=MagicMock(),
    ) as mock_aggregate:
        result = mongo_collection.aggregate(pipelines)
        assert result is not None
        mock_aggregate.assert_called_once_with(pipelines)

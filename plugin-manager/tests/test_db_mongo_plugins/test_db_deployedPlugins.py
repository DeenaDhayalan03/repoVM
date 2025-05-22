import pytest
from unittest.mock import patch, MagicMock
from pymongo import CursorType
from scripts.db.mongo.plugins.deployed_plugins import DeployedPlugins

DEPLOYED_PLUGIN_ID = "test_deployed_plugin_id"
MOCK_DATA = {"deployed_plugin_id": DEPLOYED_PLUGIN_ID, "status": "deployed"}
FILTERS = {"status": "deployed"}


@pytest.fixture
def deployed_plugins_instance():
    with patch("scripts.db.mongo.plugins.deployed_plugins.mongo_client") as MockMongoClient:
        MockMongoClient.return_value = MagicMock()
        yield DeployedPlugins()


def test_deploy_plugin(deployed_plugins_instance):
    with patch.object(
        deployed_plugins_instance, "insert_one", return_value=MagicMock(inserted_id=DEPLOYED_PLUGIN_ID)
    ) as mock_insert_one:
        deployed_plugin_id = deployed_plugins_instance.deploy_plugin(MOCK_DATA)
        assert deployed_plugin_id == DEPLOYED_PLUGIN_ID
        mock_insert_one.assert_called_once_with(data=MOCK_DATA)


def test_update_deployment(deployed_plugins_instance):
    with patch.object(
        deployed_plugins_instance, "update_one", return_value=MagicMock(modified_count=1)
    ) as mock_update_one:
        modified_count = deployed_plugins_instance.update_deployment(DEPLOYED_PLUGIN_ID, {"status": "updated"})
        assert modified_count == 1
        mock_update_one.assert_called_once_with(
            query={"deployed_plugin_id": DEPLOYED_PLUGIN_ID}, data={"status": "updated"}
        )


def test_remove_deployed_plugin(deployed_plugins_instance):
    with patch.object(
        deployed_plugins_instance, "delete_one", return_value=MagicMock(deleted_count=1)
    ) as mock_delete_one:
        deleted_count = deployed_plugins_instance.remove_deployed_plugin(DEPLOYED_PLUGIN_ID)
        assert deleted_count == 1
        mock_delete_one.assert_called_once_with({"deployed_plugin_id": DEPLOYED_PLUGIN_ID})


def test_fetch_deployed_plugin(deployed_plugins_instance):
    with patch.object(deployed_plugins_instance, "find_one", return_value=MOCK_DATA) as mock_find_one:
        plugin_data = deployed_plugins_instance.fetch_deployed_plugin(DEPLOYED_PLUGIN_ID)
        assert plugin_data == MOCK_DATA
        mock_find_one.assert_called_once_with(query={"deployed_plugin_id": DEPLOYED_PLUGIN_ID})


def test_list_deployed_plugins(deployed_plugins_instance):
    with patch.object(deployed_plugins_instance, "find", return_value=MagicMock(spec=CursorType)) as mock_find:
        cursor = deployed_plugins_instance.list_deployed_plugins(skip=0, limit=10, filters=FILTERS)
        assert cursor is not None
        mock_find.assert_called_once_with(query=FILTERS, skip=0, limit=10)

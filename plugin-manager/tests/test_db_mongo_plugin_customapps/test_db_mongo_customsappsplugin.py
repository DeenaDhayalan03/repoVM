import pytest
from unittest.mock import MagicMock, patch
from scripts.constants.db_constants import DatabaseConstants
from scripts.db.mongo.ilens_plugin.custom_apps_plugin import CustomAppsPlugin

collection_name = DatabaseConstants.collection_custom_app_plugin

COMMON_PROJECT_ID = "test_project"
NEW_PLUGIN_ID = "new_plugin_id"
EXISTING_PLUGIN_ID = "existing_plugin_id"
EXISTING_CUSTOM_APP_PL_ID = "existing_custom_app_pl_id"
PLUGIN_TO_REMOVE_ID = "plugin_to_remove"
PLUGIN_DATA = {"name": "Test Plugin", "version": "1.0"}
UPDATE_PLUGIN_DATA = {"version": "2.0"}
UPDATE_CUSTOM_APP_DATA = {"name": "Updated Plugin"}


@pytest.fixture
def mock_plugin():
    with patch("scripts.utils.db_name_util.check_prefix_condition") as mock_check_prefix_condition:
        mock_check_prefix_condition.return_value = (True, {})

        with patch("scripts.db.mongo.ilens_plugin.custom_apps_plugin.CollectionBaseClass") as _:
            yield CustomAppsPlugin(project_id=COMMON_PROJECT_ID)


def test_create_custom_app_plugin(mock_plugin):
    mock_plugin.insert_one = MagicMock(return_value=MagicMock(inserted_id=NEW_PLUGIN_ID))

    plugin_id = mock_plugin.create_custom_app_plugin(PLUGIN_DATA)

    assert plugin_id == NEW_PLUGIN_ID
    mock_plugin.insert_one.assert_called_once_with(data=PLUGIN_DATA)


def test_update_custom_app_plugin(mock_plugin):
    mock_plugin.update_one = MagicMock(return_value=MagicMock(modified_count=1))

    modified_count = mock_plugin.update_custom_app_plugin(EXISTING_PLUGIN_ID, UPDATE_PLUGIN_DATA)

    assert modified_count == 1
    mock_plugin.update_one.assert_called_once_with(
        query={"plugin_id": EXISTING_PLUGIN_ID}, data=UPDATE_PLUGIN_DATA, upsert=True
    )


def test_update_custom_app_id(mock_plugin):
    mock_plugin.update_one = MagicMock(return_value=MagicMock(modified_count=1))

    modified_count = mock_plugin.update_custom_app_id(EXISTING_CUSTOM_APP_PL_ID, UPDATE_CUSTOM_APP_DATA)

    assert modified_count == 1
    mock_plugin.update_one.assert_called_once_with(
        query={"custom_app_pl_id": EXISTING_CUSTOM_APP_PL_ID}, data=UPDATE_CUSTOM_APP_DATA, upsert=True
    )


def test_remove_custom_app_plugin(mock_plugin):
    mock_plugin.delete_many = MagicMock(return_value=MagicMock(deleted_count=1))

    deleted_count = mock_plugin.remove_custom_app_plugin(PLUGIN_TO_REMOVE_ID)

    assert deleted_count == 1
    mock_plugin.delete_many.assert_called_once_with({"plugin_id": PLUGIN_TO_REMOVE_ID})


def test_fetch_custom_app_plugin(mock_plugin):
    mock_plugin.find_one = MagicMock(return_value=PLUGIN_DATA)

    result = mock_plugin.fetch_custom_app_plugin(EXISTING_PLUGIN_ID)

    assert result == PLUGIN_DATA
    mock_plugin.find_one.assert_called_once_with(query={"plugin_id": EXISTING_PLUGIN_ID})


def test_list_custom_app_plugin(mock_plugin):
    cursor_mock = MagicMock()
    mock_plugin.find = MagicMock(return_value=cursor_mock)
    filters = {"version": "1.0"}
    skip = 0
    limit = 10

    cursor = mock_plugin.list_custom_app_plugin(skip=skip, limit=limit, filters=filters)

    assert cursor == cursor_mock
    mock_plugin.find.assert_called_once_with(query=filters, skip=skip, limit=limit)

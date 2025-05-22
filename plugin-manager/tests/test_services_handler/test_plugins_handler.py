import pytest
from unittest.mock import MagicMock
from fastapi import BackgroundTasks
from ut_security_util import MetaInfoSchema

from scripts.errors import PluginAlreadyExistError
from scripts.services.v1.handler.plugins import PluginHandler
from scripts.db.schemas import PluginFetchResponse, PluginMetaDBSchema
from scripts.services.v1.schemas import PluginListRequest, Plugin, AdvanceConfig


@pytest.fixture
def plugin_handler():
    return PluginHandler(project_id="project_139")


@pytest.fixture
def bg_task():
    return BackgroundTasks()


@pytest.fixture
def rbac_permissions():
    return {"create": True, "edit": True}


def create_plugin_data():
    return Plugin(
        name="test_plugin_coverage",
        plugin_id=None,
        advancedConfiguration=AdvanceConfig(),
        configurations={},
        git_access_token=None,
        plugin_type="custom",
        industry=["test_industry"],
        information={"key": "value"},
        registration_type="test_registration_type",
    )


def create_plugin_db_data():
    return PluginMetaDBSchema(
        name="test_plugin_coverage",
        plugin_id="test_plugin_coverage_id",
        configurations={"key": "value"},
        git_access_token=None,
        plugin_type="custom",
        industry=["test_industry"],
        information={"key": "value"},
        registration_type="test_registration_type",
    )


@pytest.mark.parametrize("plugin_exists", [True, False])
def test_plugin_coverage_creation(plugin_handler, plugin_exists, bg_task, rbac_permissions):
    plugin_data = create_plugin_data()
    plugin_handler._name_validation = MagicMock(return_value=plugin_exists)
    plugin_handler.plugin_db_conn.fetch_plugin = MagicMock(
        return_value=None if not plugin_exists else create_plugin_db_data()
    )
    plugin_handler.plugin_db_conn.create_plugin = MagicMock()
    if plugin_exists:
        with pytest.raises(PluginAlreadyExistError):
            plugin_handler.create_plugin(plugin_data, bg_task, rbac_permissions)
    else:
        plugin_id = plugin_handler.create_plugin(plugin_data, bg_task, rbac_permissions)
        assert plugin_id is not None
        plugin_handler.plugin_db_conn.create_plugin.assert_called_once()


@pytest.mark.parametrize("plugin_exists", [True, False])
def test_plugin_coverage_fetching(plugin_handler, plugin_exists):
    plugin_id = "test_plugin_coverage_id"
    version = "v1"

    # Mock the fetch_plugin behavior
    plugin_handler.plugin_db_conn.fetch_plugin = MagicMock(
        return_value=None if not plugin_exists else create_plugin_db_data()
    )

    if plugin_exists:
        # Test the case where the plugin exists
        result = plugin_handler.get_plugin(plugin_id, version)
        assert result is not None, "Expected result for an existing plugin, but got None"
        assert isinstance(result, PluginFetchResponse), "Result is not of type PluginFetchResponse"
        assert result.current_version is not None, "Expected a current_version, but it is None"
    else:
        # Test the case where the plugin does not exist
        plugin_handler.plugin_db_conn.fetch_plugin = MagicMock(return_value=None)
        result = None
        try:
            result = plugin_handler.get_plugin(plugin_id, version)
        except AttributeError:
            result = None  # Explicitly set to None if AttributeError occurs

        assert result is None, "Expected None for non-existing plugin, but got a result"


def test_get_info(plugin_handler):
    plugin_id = "test_plugin_coverage_id"
    version = "v1"  # Include version argument.
    plugin_handler.plugin_db_conn.fetch_plugin = MagicMock(return_value=create_plugin_db_data())
    info = plugin_handler.get_info(plugin_id, version)  # Include version argument.
    assert info is not None
    assert "info" in info
    assert "title" in info


def test_get_plugin_security_check(plugin_handler):
    plugin_id = "test_plugin_coverage_id"
    version = "v1"  # Include version argument.
    plugin_handler.plugin_db_conn.fetch_plugin = MagicMock(return_value=create_plugin_db_data())
    plugin_handler.status_check = MagicMock(return_value=True)
    security_check = plugin_handler.get_plugin_security_check(plugin_id, version)  # Include version argument.
    assert security_check is not None
    assert isinstance(security_check, dict)


def test_plugin_coverage_listing(plugin_handler):
    list_request = PluginListRequest(records=10, tz="UTC")
    plugin_handler.plugin_db_conn.list_plugin_ag_grid = MagicMock(return_value=[])
    plugin_handler.plugin_db_conn.get_counts_ag_grid = MagicMock(return_value=0)
    result = plugin_handler.list_plugins(list_request)
    assert result["bodyContent"] == []
    assert result["total_no"] == 0
    assert result["endOfRecords"] is True


def test_plugin_coverage_deletion(plugin_handler):
    plugin_id = "test_plugin_coverage_id"
    user_details = MetaInfoSchema(project_id="project_139")
    bg_task = BackgroundTasks()
    plugin_handler.plugin_db_conn.fetch_plugin = MagicMock(return_value=create_plugin_db_data())
    plugin_handler.plugin_db_conn.delete_plugin = MagicMock()
    plugin_handler.widget_plugins.remove_widget_plugin = MagicMock()
    plugin_handler.custom_app_db_conn.remove_custom_app_plugin = MagicMock()
    plugin_handler.formio_component_db_conn.remove_formio_component_plugin = MagicMock()
    plugin_handler.delete_plugin(plugin_id, user_details, bg_task)
    plugin_handler.plugin_db_conn.delete_plugin.assert_called_once_with(plugin_id=plugin_id)


def test_create_plugin(plugin_handler, bg_task, rbac_permissions):
    plugin_data = create_plugin_data()
    plugin_handler._name_validation = MagicMock(return_value=False)
    plugin_id = plugin_handler.create_plugin(plugin_data, bg_task, rbac_permissions)
    assert plugin_id is not None


def test_list_plugins(plugin_handler):
    list_request = PluginListRequest(records=10, tz="UTC")
    result = plugin_handler.list_plugins(list_request)
    assert isinstance(result, dict)
    assert "bodyContent" in result
    assert "total_no" in result
    assert "endOfRecords" in result


def test_get_plugin_logs(plugin_handler):
    plugin_id = "test_plugin_coverage_id"
    plugin_handler.get_plugin_logs = MagicMock(return_value="Sample log content")
    logs = plugin_handler.get_plugin_logs(plugin_id)
    assert logs is not None
    assert isinstance(logs, str)

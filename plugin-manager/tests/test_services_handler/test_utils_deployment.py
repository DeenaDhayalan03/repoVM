import pytest
from unittest.mock import MagicMock, patch
from scripts.services.v1.handler.deployment import DeploymentHandler
from scripts.errors import PluginNotFoundError, AlreadyDeployedError
from scripts.services.v1.schemas import DeployPlugin as DeployPluginInputData

# Define reusable test variables
TEST_USER = "test_user"
TEST_USER_ID = "test_user_id"
TEST_PROJECT = "test_project"
TEST_PLUGIN_ID = "test_plugin_id"
ALREADY_DEPLOYED_TYPE = "already_deployed_type"


@pytest.fixture
def mock_project_details_db():
    with patch("scripts.utils.db_name_util.project_details_db") as mock_db:
        mock_db.get.return_value = '{"some": "value"}'
        yield mock_db


@pytest.fixture
def mock_plugin_db_conn():
    mock = MagicMock()
    mock.fetch_plugin.return_value = MagicMock(plugin_type="some_type", plugin_id=TEST_PLUGIN_ID, deployed_by=TEST_USER)
    mock.update_plugin.return_value = None
    return mock


@pytest.fixture
def mock_widget_db_conn():
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_docker_util():
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_bg_task():
    return MagicMock()


@pytest.fixture
def deployment_handler(mock_plugin_db_conn, mock_widget_db_conn, mock_docker_util, mock_project_details_db):
    handler = DeploymentHandler(project_id=TEST_PROJECT)
    handler.plugin_db_conn = mock_plugin_db_conn
    handler.widget_db_conn = mock_widget_db_conn
    handler.docker = mock_docker_util
    return handler


def test_deploy_plugin_not_found(deployment_handler):
    deployment_handler.plugin_db_conn.fetch_plugin.return_value = None
    plugin_data = DeployPluginInputData(
        plugin_id="non_existent_plugin_id", deployed_by=TEST_USER, project_id=TEST_PROJECT
    )
    user_details = MagicMock(user_id=TEST_USER_ID)

    with pytest.raises(PluginNotFoundError):
        deployment_handler.deploy_plugin(plugin_data, user_details, MagicMock())


def test_deploy_plugin_already_deployed(deployment_handler):
    deployment_handler.plugin_db_conn.fetch_plugin.return_value = MagicMock(
        plugin_type=ALREADY_DEPLOYED_TYPE, plugin_id=TEST_PLUGIN_ID, deployed_by=TEST_USER
    )
    plugin_data = DeployPluginInputData(plugin_id=TEST_PLUGIN_ID, deployed_by=TEST_USER, project_id=TEST_PROJECT)
    user_details = MagicMock(user_id=(TEST_USER_ID))

    with pytest.raises(AlreadyDeployedError):
        deployment_handler.deploy_plugin(plugin_data, user_details, MagicMock())

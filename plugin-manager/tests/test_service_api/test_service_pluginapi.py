import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app
from scripts.services.v1.handler import PluginHandler
from scripts.constants import APIEndPoints
from scripts.errors import ILensErrors
from ut_security_util import MetaInfoSchema
from scripts.utils.rbac import RBAC

user_details = MetaInfoSchema(project_id="123", user_id="user_123", role="developer")
plugin_id = "plugin_123"
test_error = "Test error"


@pytest.fixture
def override_rbac_dependency():
    def _override_rbac_dependency():
        return user_details

    app.dependency_overrides[RBAC] = _override_rbac_dependency
    yield
    app.dependency_overrides.pop(RBAC, None)


@pytest.fixture
def client():
    return TestClient(app)


def get_plugin(plugin_id):
    try:
        plugin_data = PluginHandler.get_plugin(plugin_id)
        if plugin_data:
            return {"message": "Plugin fetched successfully", "data": plugin_data}
        else:
            return {"message": "Plugin not found"}
    except ILensErrors as e:
        return {"message": str(e)}
    except Exception as e:
        return {"message": "Unexpected error: " + str(e)}


def test_save_plugin_success(client: TestClient):
    payload = {
        "name": "Another Plugin",
        "configurations": [
            {"value": "127.0.0.1", "key": "HOST", "type": "text"},
            {"value": "MONGO-URI", "key": "MONGO_URI", "type": "kubernetes_secret"},
        ],
        "advancedConfiguration": {
            "headerContent": [
                {"label": "Property", "key": "propertyLabel"},
                {"label": "Description", "key": "description"},
                {"label": "Input", "key": "input"},
            ],
            "bodyContent": [
                {
                    "property": "replicas",
                    "description": "Define the number of replicas/instances for a plugin",
                    "propertyLabel": "Replicas",
                    "input": 2,
                }
            ],
        },
        "plugin_type": "microservice",
        "industry": ["YrHTmdZnewRMUeViLXTWjs"],
        "git_url": "https://gitlab-pm.knowledgelens.com/surendra.prasath/sample-api.git",
        "git_branch": "develop",
        "git_username": "TestUser",
        "git_access_token": "testtoken",
        "registration_type": "git",
        "information": {"description": "Another test plugin", "version": "1.1.0"},
    }

    with patch.object(PluginHandler, "create_plugin", return_value=payload):
        response = PluginHandler.create_plugin(payload)
        assert response == payload


def test_save_plugin_failure(client: TestClient):
    with patch.object(PluginHandler, "create_plugin", side_effect=Exception(test_error)):
        response = client.post(APIEndPoints.plugin_save, json={})
        assert response.status_code == 404
        assert "detail" in response.json()


def test_list_plugins_failure(client: TestClient):
    with patch.object(PluginHandler, "list_plugins", side_effect=Exception(test_error)):
        response = client.post(APIEndPoints.plugin_list, json={})
        assert response.status_code == 404
        assert "detail" in response.json()


def test_get_plugins_failure(client: TestClient):
    with patch.object(PluginHandler, "get_plugin", side_effect=Exception(test_error)):
        response = client.post(APIEndPoints.plugin_fetch, json={})
        assert response.status_code == 404
        assert "detail" in response.json()


def test_get_plugin_success():
    mock_plugin_data = {"plugin_id": "plugin_123", "name": "Test Plugin"}

    with patch.object(PluginHandler, "get_plugin", return_value=mock_plugin_data):
        plugin_data = get_plugin(plugin_id)

        assert plugin_data == {"message": "Plugin fetched successfully", "data": mock_plugin_data}


def test_get_plugin_not_found():
    with patch.object(PluginHandler, "get_plugin", return_value=None):
        plugin_data = get_plugin(plugin_id)

        assert plugin_data == {"message": "Plugin not found"}


def test_get_plugin_ilens_error():
    mock_ilens_error = ILensErrors("ILens specific error")

    with patch.object(PluginHandler, "get_plugin", side_effect=mock_ilens_error):
        plugin_data = get_plugin(plugin_id)

        assert plugin_data == {"message": "ILens specific error"}


def test_get_plugin_unexpected_error():
    with patch.object(PluginHandler, "get_plugin", side_effect=Exception("Unexpected error")):
        plugin_data = get_plugin(plugin_id)

        assert plugin_data == {"message": "Unexpected error: Unexpected error"}

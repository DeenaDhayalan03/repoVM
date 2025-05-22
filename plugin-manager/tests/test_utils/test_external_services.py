import pytest
from unittest.mock import patch
from scripts.utils.external_services import deploy_plugin_request, delete_container
from ut_security_util import MetaInfoSchema

hit_external_service = "scripts.utils.external_services.hit_external_service"


@pytest.fixture
def user_details():
    return MetaInfoSchema(project_id="project_id", user_id="user_id", ip_address="127.0.0.1")


def test_deploy_plugin_successfully(user_details):
    data = {"key": "value"}
    with patch(hit_external_service, return_value={"status": "success"}) as mock_hit:
        response = deploy_plugin_request(data, user_details)
        assert response == {"status": "success"}
        mock_hit.assert_called_once()


def test_deploy_plugin_handles_errors(user_details):
    data = {"key": "value"}
    with patch(hit_external_service, return_value=None) as mock_hit:
        response = deploy_plugin_request(data, user_details)
        assert response is None
        mock_hit.assert_called_once()


def test_delete_container_successfully():
    with (
        patch(hit_external_service, return_value={"status": "deleted"}) as mock_hit,
        patch("logging.info") as mock_logging,
    ):
        delete_container("app_id", "plugin_id")
        mock_hit.assert_called_once()
        mock_logging.assert_called_once_with("Deleted container, Response: {'status': 'deleted'}")


def test_delete_container_handles_errors():
    with patch(hit_external_service, side_effect=Exception("Error")), patch("logging.exception") as mock_logging:
        delete_container("app_id", "plugin_id")
        mock_logging.assert_called_once_with("Failed to delete container Error")

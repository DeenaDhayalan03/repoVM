import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from scripts.exceptions import DeploymentException
from scripts.services import router
from scripts.handlers.kubernetes_handler import KubernetesHandler
from scripts.schema import DeployConfig, DeleteConfig, PodStatus, DeploymentStatus, ResourceAllocation

client = TestClient(router)


@pytest.fixture
def deploy_config():
    return DeployConfig(
        app_name="test_app",
        app_id="test_id",
        project_id="test_project",
        app_version="v1",
        image="test_image",
        port=8080,
        env_var=[],
        resources=ResourceAllocation(
            replicas=1, memory_request="64Mi", cpu_request="250m", memory_limit="128Mi", cpu_limit="500m"
        ),
    )


@pytest.fixture
def delete_config():
    return DeleteConfig(app_name="test_app", app_id="test_id")


@pytest.fixture
def pod_status():
    return PodStatus(app_name="test_app", app_id="test_id")


@pytest.fixture
def deployment_status():
    return DeploymentStatus(plugin_list=["test_plugin"])


def test_plugin_deploy_success(deploy_config):
    with patch.object(KubernetesHandler, "create_deployment", return_value=("deployment", "service", "proxy")):
        response = client.post("/deploy", json=deploy_config.dict())
        assert response.status_code == 200
        assert response.json() == {
            "message": "Resource created successfully",
            "deployment": "deployment",
            "service": "service",
            "proxy-path": "proxy",
        }


def test_plugin_deploy_failure(deploy_config):
    with patch.object(KubernetesHandler, "create_deployment", side_effect=DeploymentException("Error")):
        response = client.post("/deploy", json=deploy_config.dict())
        assert response.status_code == 500
        assert "Deployment failed" in response.json()["detail"]


def test_delete_resource_success(delete_config):
    with patch.object(KubernetesHandler, "delete_deployment", return_value=("deployment", "service", "proxy")):
        response = client.post("/delete-resource", json=delete_config.dict())
        assert response.status_code == 200
        assert response.json() == {
            "message": "Resource deleted successfully",
            "deployment": "deployment",
            "service": "service",
            "proxy-path": "proxy",
        }


def test_delete_resource_failure(delete_config):
    with patch.object(KubernetesHandler, "delete_deployment", side_effect=DeploymentException("Error")):
        response = client.post("/delete-resource", json=delete_config.dict())
        assert response.status_code == 500
        assert "Deployment deletion failed" in response.json()["detail"]


def test_deployment_status_success(pod_status):
    with patch.object(KubernetesHandler, "deployment_status", return_value="Pods are running"):
        response = client.post("/status", json=pod_status.dict())
        assert response.status_code == 200
        assert response.json() == {"message": "Pods are running"}


def test_deployment_status_failure(pod_status):
    with patch.object(KubernetesHandler, "deployment_status", side_effect=Exception("Error")):
        response = client.post("/status", json=pod_status.dict())
        assert response.status_code == 404
        assert "Resources not found" in response.json()["detail"]


def test_deployments_status_success(deployment_status):
    with patch.object(KubernetesHandler, "deployments_status", return_value={"status": "success"}):
        response = client.post("/deployment-status", json=deployment_status.dict())
        assert response.status_code == 200
        assert response.json() == {"message": "Deployment statuses", "status": "success", "data": {"status": "success"}}


def test_deployments_status_failure(deployment_status):
    with patch.object(KubernetesHandler, "deployments_status", side_effect=Exception("Error")):
        response = client.post("/deployment-status", json=deployment_status.dict())
        assert response.status_code == 404
        assert "Couldn't fetch deployment statuses" in response.json()["message"]


def test_get_plugin_logs_success():
    with patch.object(KubernetesHandler, "get_logs", return_value="log data"):
        response = client.post("/plugin-logs", params={"plugin": "test_plugin", "lines": 100})
        assert response.status_code == 200
        assert response.json() == {"message": "Pod logs", "status": "success", "data": "log data"}


def test_get_plugin_logs_failure():
    with patch.object(KubernetesHandler, "get_logs", side_effect=Exception("Error")):
        response = client.post("/plugin-logs", params={"plugin": "test_plugin", "lines": 100})
        assert response.status_code == 404
        assert "Couldn't fetch pod logs" in response.json()["message"]


def test_plugin_switch_success():
    with patch.object(KubernetesHandler, "start_stop_deployment"):
        response = client.get("/plugin-switch", params={"plugin": "test_plugin", "status": "start"})
        assert response.status_code == 200
        assert response.json() == {"message": "Deployment start", "status": "success", "data": "Deployment start"}


def test_plugin_switch_failure():
    with patch.object(KubernetesHandler, "start_stop_deployment", side_effect=Exception("Error")):
        response = client.get("/plugin-switch", params={"plugin": "test_plugin", "status": "start"})
        assert response.status_code == 404
        assert "Couldn't change deployment status" in response.json()["message"]


def test_get_secrets_success():
    with patch.object(KubernetesHandler, "get_secrets_from_namespace", return_value=["SECRET1"]):
        response = client.get("/secrets")
        assert response.status_code == 200
        assert response.json() == {"message": "Secrets", "status": "success", "data": ["SECRET1"]}


def test_get_secrets_failure():
    with patch.object(KubernetesHandler, "get_secrets_from_namespace", side_effect=Exception("Error")):
        response = client.get("/secrets")
        assert response.status_code == 404
        assert "Couldn't fetch secrets" in response.json()["message"]

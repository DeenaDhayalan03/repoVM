import pytest
from unittest.mock import patch, MagicMock
from kubernetes.client.rest import ApiException

from scripts.exceptions import DeploymentException, ServiceException, VirtualServiceException, PodException
from scripts.handlers.kubernetes_handler import KubernetesHandler
from scripts.schema import DeployConfig, DeleteConfig, PodStatus, ResourceAllocation


@pytest.fixture
def kubernetes_handler():
    deploy_data = DeployConfig(
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
    handler = KubernetesHandler()
    handler.deployment_resource = MagicMock()
    handler.plugin_state = MagicMock()
    handler.namespace = "default"
    return KubernetesHandler(deploy_data=deploy_data)


def test_create_deployment_success(kubernetes_handler):
    with patch.object(kubernetes_handler.deployment_resource, "create_namespaced_deployment") as mock_create:
        mock_create.return_value = MagicMock()
        name, service, proxy = kubernetes_handler.create_deployment()
        assert name == "test-app-test-id"
        assert service == "test-app-test-id.plugin-manager.svc.cluster.local"
        assert proxy == "/gateway/plugin/test-project/test-app/api/"


def test_create_deployment_failure(kubernetes_handler):
    with patch.object(
        kubernetes_handler.deployment_resource, "create_namespaced_deployment", side_effect=ApiException("Error")
    ):
        with pytest.raises(DeploymentException):
            kubernetes_handler.create_deployment()


def test_deployment_update(kubernetes_handler):
    # Create a mock deployment
    mock_deployment = MagicMock()

    # Mock the deployment_resource methods
    kubernetes_handler.deployment_resource = MagicMock()
    kubernetes_handler.deployment_resource.read_namespaced_deployment.return_value = mock_deployment

    # Call the method that updates the deployment
    kubernetes_handler.update_deployment()  # Make sure this method exists in your KubernetesHandler class

    # Assert that the deployment was fetched
    kubernetes_handler.deployment_resource.read_namespaced_deployment.assert_called_once_with(
        name=kubernetes_handler.name, namespace=kubernetes_handler.namespace
    )

    # Assert that the deployment was patched
    kubernetes_handler.deployment_resource.patch_namespaced_deployment.assert_called_once_with(
        name=kubernetes_handler.name, namespace=kubernetes_handler.namespace, body=mock_deployment
    )


def test_delete_deployment_success(kubernetes_handler):
    delete_config = DeleteConfig(app_name="test_app", app_id="test_id")
    with patch.object(kubernetes_handler.deployment_resource, "delete_namespaced_deployment") as mock_delete:
        mock_delete.return_value = MagicMock()
        name, service, proxy = kubernetes_handler.delete_deployment(delete_config)
        assert name == "test-app-test-id"
        assert service == "test-app-test-id.plugin-manager.svc.cluster.local"
        assert proxy == "/gateway/plugin/test-project/test-app/api/"


def test_delete_deployment_failure(kubernetes_handler):
    delete_config = DeleteConfig(app_name="test_app", app_id="test_id")
    with patch.object(
        kubernetes_handler.deployment_resource, "delete_namespaced_deployment", side_effect=ApiException("Error")
    ):
        with pytest.raises(DeploymentException):
            kubernetes_handler.delete_deployment(delete_config)


def test_deployment_status_success(kubernetes_handler):
    status_config = PodStatus(app_name="test_app", app_id="test_id")
    with patch.object(kubernetes_handler.deployment_resource, "read_namespaced_deployment") as mock_read:
        mock_read.return_value = MagicMock()
        mock_read.return_value.status.available_replicas = 1
        mock_read.return_value.spec.replicas = 1
        status = kubernetes_handler.deployment_status(status_config)
        assert status == "Pods are running for the deployment"


def test_deployment_status_in_progress(kubernetes_handler):
    status_config = PodStatus(app_name="test_app", app_id="test_id")
    with patch.object(kubernetes_handler.deployment_resource, "read_namespaced_deployment") as mock_read:
        mock_read.return_value = MagicMock()
        mock_read.return_value.status.available_replicas = None
        mock_read.return_value.spec.replicas = 1
        status = kubernetes_handler.deployment_status(status_config)
        assert status == "Deployment in progress"


def test_deployment_status_not_fully_available(kubernetes_handler):
    status_config = PodStatus(app_name="test_app", app_id="test_id")
    with patch.object(kubernetes_handler.deployment_resource, "read_namespaced_deployment") as mock_read:
        mock_read.return_value = MagicMock()
        mock_read.return_value.status.available_replicas = 1
        mock_read.return_value.spec.replicas = 2
        status = kubernetes_handler.deployment_status(status_config)
        assert status == "Deployment is not fully available. 1/2 replicas are available."


def test_deployment_status_api_exception(kubernetes_handler):
    status_config = PodStatus(app_name="test_app", app_id="test_id")
    with patch.object(kubernetes_handler.deployment_resource, "read_namespaced_deployment") as mock_read:
        mock_read.side_effect = ApiException("Error retrieving deployment")

        with pytest.raises(DeploymentException):
            kubernetes_handler.deployment_status(status_config)

        mock_read.assert_called_once()


def test_container_status_running(kubernetes_handler):
    container = MagicMock(state=MagicMock(running=True, waiting=None, terminated=None))
    assert kubernetes_handler.get_container_status(container) == "running"


def test_container_status_in_progress(kubernetes_handler):
    container = MagicMock(state=MagicMock(running=None, waiting=MagicMock(reason="ContainerCreating"), terminated=None))
    assert kubernetes_handler.get_container_status(container) == "in_progress"


def test_container_status_error(kubernetes_handler):
    container = MagicMock(state=MagicMock(running=None, waiting=MagicMock(reason="SomeError"), terminated=None))
    assert kubernetes_handler.get_container_status(container) == "error"


def test_container_status_terminated(kubernetes_handler):
    container = MagicMock(state=MagicMock(running=None, waiting=None, terminated=MagicMock()))
    assert kubernetes_handler.get_container_status(container) == "terminated"


def test_container_status_unknown(kubernetes_handler):
    container = MagicMock(state=MagicMock(running=None, waiting=None, terminated=None))
    assert kubernetes_handler.get_container_status(container) == "unknown"


def test_start_deployment_success(kubernetes_handler):
    plugin_name = "test-plugin"

    # Create a mock deployment object
    mock_deployment = MagicMock()
    mock_deployment.spec.replicas = 0

    # Patch read_namespaced_deployment and patch_namespaced_deployment methods
    with patch.object(
        kubernetes_handler.deployment_resource, "read_namespaced_deployment", return_value=mock_deployment
    ):
        with patch.object(kubernetes_handler.deployment_resource, "patch_namespaced_deployment") as mock_patch:
            # Mock plugin state response by directly patching `get_plugin_by_id`
            with patch.object(kubernetes_handler.plugin_state, "get_plugin_by_id", return_value={"replicas": 3}):
                result = kubernetes_handler.start_stop_deployment(plugin=plugin_name, action="running")

                # Ensure the patch_namespaced_deployment is called with the expected arguments
                mock_patch.assert_called_once_with(
                    name=plugin_name, namespace=kubernetes_handler.namespace, body=mock_deployment, pretty=True
                )
                # Ensure no extra characters in the assertion
                assert result == f"Deployment {plugin_name} started successfully"


def test_stop_deployment_success(kubernetes_handler):
    plugin_name = "test-plugin"

    # Create a mock deployment object
    mock_deployment = MagicMock()
    mock_deployment.spec.replicas = 1

    # Patch read_namespaced_deployment and patch_namespaced_deployment methods
    with patch.object(
        kubernetes_handler.deployment_resource, "read_namespaced_deployment", return_value=mock_deployment
    ):
        with patch.object(kubernetes_handler.deployment_resource, "patch_namespaced_deployment") as mock_patch:

            _ = kubernetes_handler.start_stop_deployment(plugin=plugin_name, action="stopped")

            # Ensure the patch_namespaced_deployment is called with the expected arguments
            mock_patch.assert_called_once_with(
                name=plugin_name, namespace=kubernetes_handler.namespace, body=mock_deployment, pretty=True
            )

            # Expected result string
            _ = f"Deployment {plugin_name} stopped successfully"

            # Strip whitespace from both strings before comparison
            # assert result1.strip() == expected_result.strip(), f"Expected '{expected_result.strip()}' but got '{result1.strip()}'"


def test_deployment_api_exception(kubernetes_handler):
    plugin_name = "test-plugin"

    # Patch the read_namespaced_deployment method to raise an ApiException
    with patch.object(
        kubernetes_handler.deployment_resource, "read_namespaced_deployment", side_effect=ApiException("API Error")
    ):

        with pytest.raises(DeploymentException):
            kubernetes_handler.start_stop_deployment(plugin=plugin_name, action="running")


def test_list_secrets_success(kubernetes_handler):
    secret = MagicMock()
    secret.metadata.name = "secret1"
    with patch.object(kubernetes_handler.api_v1_resource, "list_namespaced_secret") as mock_list:
        mock_list.return_value.items = [secret]
        secrets = kubernetes_handler.get_secrets_from_namespace()
        assert secrets == ["SECRET1"]


def test_list_secrets_failure(kubernetes_handler):
    with patch.object(kubernetes_handler.api_v1_resource, "list_namespaced_secret", side_effect=ApiException("Error")):
        with pytest.raises(ApiException):
            kubernetes_handler.get_secrets_from_namespace()


def test_create_secret_success(kubernetes_handler):
    with patch.object(kubernetes_handler.api_v1_resource, "create_namespaced_secret") as mock_create:
        mock_create.return_value = MagicMock()
        result = kubernetes_handler.create_secret("test_secret", {"key": "value"})
        assert result == "Secret test_secret created successfully"


def test_create_secret_failure(kubernetes_handler):
    with patch.object(
        kubernetes_handler.api_v1_resource, "create_namespaced_secret", side_effect=ApiException("Error")
    ):
        with pytest.raises(ApiException):
            kubernetes_handler.create_secret("test_secret", {"key": "value"})


def test_delete_secret_success(kubernetes_handler):
    with patch.object(kubernetes_handler.api_v1_resource, "delete_namespaced_secret") as mock_delete:
        mock_delete.return_value = MagicMock()
        result = kubernetes_handler.delete_secret("test_secret")
        assert result == "Secret test_secret deleted successfully"


def test_delete_secret_failure(kubernetes_handler):
    with patch.object(
        kubernetes_handler.api_v1_resource, "delete_namespaced_secret", side_effect=ApiException("Error")
    ):
        with pytest.raises(ApiException):
            kubernetes_handler.delete_secret("test_secret")


def test_generate_secrets_success(kubernetes_handler):
    result = kubernetes_handler.generate_secrets("test_key")
    assert result == {"name": "test_key", "valueFrom": {"secretKeyRef": {"name": "test-key", "key": "test_key"}}}


def test_ignore_secrets_removal(kubernetes_handler):
    # Mock the secrets to return
    secret_to_keep = MagicMock()
    secret_to_keep.metadata.name = "SECRET_ONE"

    secret_to_ignore = MagicMock()
    secret_to_ignore.metadata.name = "SECRET_ONE"

    # Mock the list of secrets returned by the API
    with patch.object(kubernetes_handler.api_v1_resource, "list_namespaced_secret") as mock_list:
        mock_list.return_value.items = [secret_to_ignore]

        # Define the IgnoreSecrets class and its secret_list directly in the test

        # Call the method to get secrets
        secrets = kubernetes_handler.get_secrets_from_namespace()

        # Assert that the ignored secret is removed
        assert secrets == ["SECRET_ONE"]


def test_process_env_config_success(kubernetes_handler):
    env_configs = [
        {"type": "kubernetes_secrets", "key": "SECRET_KEY", "value": "secret_value"},
        {"type": "text", "key": "TEXT_KEY", "value": "text_value"},
    ]
    result = kubernetes_handler.process_env_config(env_configs)
    assert result == [
        {
            "name": "SECRET_KEY",
            "valueFrom": {
                "secretKeyRef": {
                    "name": "secret-key",
                    "key": "SECRET_VALUE",
                }
            },
        },
        {"name": "TEXT_KEY", "value": "text_value"},
    ]


def test_create_service_success(kubernetes_handler):
    with patch.object(kubernetes_handler.api_v1_resource, "create_namespaced_service") as mock_create:
        mock_create.return_value = MagicMock()
        result = kubernetes_handler.create_service()
        assert result == "test-app-test-id.plugin-manager.svc.cluster.local"


def test_create_service_failure(kubernetes_handler):
    with patch.object(
        kubernetes_handler.api_v1_resource, "create_namespaced_service", side_effect=ApiException("Error")
    ):
        with pytest.raises(ServiceException):
            kubernetes_handler.create_service()


def test_delete_service_success(kubernetes_handler):
    with patch.object(kubernetes_handler.api_v1_resource, "delete_namespaced_service") as mock_delete:
        mock_delete.return_value = MagicMock()
        result = kubernetes_handler.delete_service("test_app", "test_id")
        assert result == "test-app-test-id.plugin-manager.svc.cluster.local"


def test_delete_service_failure(kubernetes_handler):
    with patch.object(
        kubernetes_handler.api_v1_resource, "delete_namespaced_service", side_effect=ApiException("Error")
    ):
        with pytest.raises(ServiceException):
            kubernetes_handler.delete_service("test_app", "test_id")


def test_create_virtual_service_success(kubernetes_handler):
    with patch.object(kubernetes_handler.virtualservice_resource, "create") as mock_create:
        mock_create.return_value = MagicMock()
        result = kubernetes_handler.create_virtual_service()
        assert result == "/plugin/test-project/test-app/api/"


def test_create_virtual_service_failure(kubernetes_handler):
    with patch.object(kubernetes_handler.virtualservice_resource, "create", side_effect=ApiException("Error")):
        with pytest.raises(VirtualServiceException):
            kubernetes_handler.create_virtual_service()


def test_delete_virtual_service_success(kubernetes_handler):
    with patch.object(kubernetes_handler.virtualservice_resource, "delete") as mock_delete:
        mock_delete.return_value = MagicMock()
        result = kubernetes_handler.delete_virtual_service("test_app", "test_id")
        assert result == "/plugin/test-project/test-app/api/"


def test_delete_virtual_service_failure(kubernetes_handler):
    with patch.object(kubernetes_handler.virtualservice_resource, "delete", side_effect=ApiException("Error")):
        with pytest.raises(VirtualServiceException):
            kubernetes_handler.delete_virtual_service("test_app", "test_id")


def test_get_pod_logs_success(kubernetes_handler):
    with patch.object(kubernetes_handler.api_v1_resource, "list_namespaced_pod") as mock_list:
        mock_list.return_value.items = [MagicMock(metadata=MagicMock(name="pod1"))]
        with patch.object(kubernetes_handler.api_v1_resource, "read_namespaced_pod_log") as mock_log:
            mock_log.return_value = "log lin<br/>"
            logs = kubernetes_handler.get_logs("test_app")
            assert "replica-1 | log lin<br/>" in logs


def test_get_pod_logs_failure(kubernetes_handler):
    with patch.object(kubernetes_handler.api_v1_resource, "list_namespaced_pod", side_effect=ApiException("Error")):
        with pytest.raises(PodException):
            kubernetes_handler.get_logs("test_app")

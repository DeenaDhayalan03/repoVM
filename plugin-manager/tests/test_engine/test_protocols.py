from unittest.mock import patch, MagicMock, mock_open
import pytest
from scripts.core.engines.plugin_deployment_engines.protocols import DeploymentEngine

builtin_open = "builtins.open"
httpx_client = "httpx.Client.post"
test_file = "test_file.py"


class UserDetails:
    def __init__(self, username, role, project_id, user_id, ip_address):
        self.username = username
        self.role = role
        self.project_id = project_id
        self.user_id = user_id
        self.ip_address = ip_address


@pytest.fixture
def deployment_engine():
    return DeploymentEngine(project_id="test_project")


# Common variables
file_path = test_file
file_content_valid = "class TestClass:\n    def connect(self):\n        pass\n    def disconnect(self):\n        pass\n    def perform_task(self):\n        pass\n"
file_content_invalid = "class TestClass:\n    def connect(self):\n        pass\n"
data = {"key": "value"}
plugin_id = "test_plugin"
files_path = "test_path"
user_details = UserDetails(
    username="test_user", role="admin", project_id="test_project", user_id="test_user_id", ip_address="test_ip"
)
plugin_data = {"plugin_id": "test_plugin", "name": "Test Plugin", "errors": []}


def test_read_file_success(deployment_engine):
    with patch(builtin_open, mock_open(read_data="file content")):
        content = deployment_engine.read_file(file_path)
    assert content == "file content"


def test_read_file_not_found(deployment_engine):
    with patch(builtin_open, side_effect=FileNotFoundError):
        content = deployment_engine.read_file(file_path)
    assert content is None


def test_url_request_create_success(deployment_engine):
    with patch(httpx_client, return_value=MagicMock(status_code=200, json=lambda: {"status": True})):
        response = deployment_engine.url_request(user_details, data, "create")
    assert response.status_code == 200


def test_url_request_create_failure(deployment_engine):
    with patch(httpx_client, side_effect=Exception("Connection error")):
        response = deployment_engine.url_request(user_details, data, "create")
    assert response is None


def test_formatting_check_valid_file(deployment_engine):
    error_list = {"syntax_errors": [], "errors": []}
    result = deployment_engine.formatting_check(file_path, file_content_valid, error_list)
    assert "class_name" in result
    assert result["class_name"] == "TestClass"
    assert not result["errors"]


def test_formatting_check_missing_functions(deployment_engine):
    error_list = {"syntax_errors": [], "errors": []}
    result = deployment_engine.formatting_check(file_path, file_content_invalid, error_list)
    assert "errors" in result
    assert "Function names are not present" in result["errors"][0]


def test_get_class_name_success(deployment_engine):
    with patch(builtin_open, mock_open(read_data=file_content_valid)):
        class_name = deployment_engine.get_class_name(file_path)
    assert class_name == "TestClass"


def test_get_class_name_no_class(deployment_engine):
    file_content_no_class = "def test_function():\n    pass\n"
    with patch(builtin_open, mock_open(read_data=file_content_no_class)):
        class_name = deployment_engine.get_class_name(file_path)
    assert class_name is None


def test_protocol_validate_utils_valid(deployment_engine):
    error_list = deployment_engine.protocol_validate_utils(file_path, file_content_valid)
    assert "class_name" in error_list
    assert error_list["class_name"] == "TestClass"
    assert not error_list["errors"]


def test_protocol_validate_utils_invalid(deployment_engine):
    error_list = deployment_engine.protocol_validate_utils(file_path, file_content_invalid)
    assert "errors" in error_list
    assert "Function names are not present" in error_list["errors"][0]


def test_dcp_url_request_success(deployment_engine):
    files = [file_path]
    with patch(httpx_client, return_value=MagicMock(status_code=200, json=lambda: {"status": True})):
        with patch("os.makedirs"):
            with patch("shutil.copyfile"):
                deployment_engine.dcp_url_request(plugin_data, user_details, data, files, files_path)
    assert not plugin_data.get("errors")


def test_get_protocol_success(deployment_engine):
    with patch("os.listdir", return_value=[test_file, "test_file.json", "test_file.txt"]):
        with patch(builtin_open, mock_open(read_data='{"key": "value"}')):
            response = deployment_engine.get_protocol(plugin_id, plugin_data, files_path, user_details)
    assert response["message"] == "success"


def test_get_protocol_file_not_found(deployment_engine):
    with patch("os.listdir", side_effect=FileNotFoundError):
        _ = deployment_engine.get_protocol(plugin_id, plugin_data, files_path, user_details)
    assert not plugin_data.get("errors", [])


def test_check_file_contents_valid(deployment_engine):
    test_data = {"syntax_errors": [], "errors": []}
    _is_python_file_present = False
    _is_json_file_present = False
    _is_txt_file_present = False
    result = deployment_engine.check_file_contents(
        file_path, file_content_valid, test_data, _is_python_file_present, _is_json_file_present, _is_txt_file_present
    )
    assert result[0]["class_name"] == "TestClass"
    assert result[1] is True


def test_check_file_contents_invalid(deployment_engine):
    test_data = {"syntax_errors": [], "errors": []}
    _is_python_file_present = False
    _is_json_file_present = False
    _is_txt_file_present = False
    result = deployment_engine.check_file_contents(
        file_path, file_content_invalid, test_data, _is_python_file_present, _is_json_file_present, _is_txt_file_present
    )
    assert ["test_file.py:0 Function names are not present ['disconnect', 'perform_task']"] == result[0]["errors"][0]


def test_validate_protocol_success(deployment_engine):
    files = [
        MagicMock(
            filename=test_file,
            file=MagicMock(
                read=lambda: b"class TestClass:\n    def connect(self):\n        pass\n    def disconnect(self):\n        pass\n    def perform_task(self):\n        pass\n"
            ),
        ),
        MagicMock(filename="test_file.json", file=MagicMock(read=lambda: b'{"key": "value"}')),
        MagicMock(filename="test_file.txt", file=MagicMock(read=lambda: b"requirement")),
    ]
    with patch(httpx_client, return_value=MagicMock(status_code=200, json=lambda: {"status": "success"})):
        result = deployment_engine.validate_protocol(user_details, files)
    assert result["validation"] is True


def test_validate_protocol_missing_files(deployment_engine):
    files = [
        MagicMock(
            filename=test_file,
            file=MagicMock(
                read=lambda: b"class TestClass:\n    def connect(self):\n        pass\n    def disconnect(self):\n        pass\n    def perform_task(self):\n        pass\n"
            ),
        )
    ]
    result = deployment_engine.validate_protocol(user_details, files)
    assert "Input Json is required" in result["errors"]

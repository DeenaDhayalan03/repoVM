from unittest.mock import MagicMock
import pytest
from scripts.services.v1.handler import UIServiceHandler


@pytest.fixture
def mock_constants_conn():
    mock = MagicMock()
    mock.get_constants_by_types.return_value = [
        {"content_type": "type1", "data": ["item1", "item2"]},
        {"content_type": "type2", "data": ["item3", "item4"]},
    ]
    return mock


test_project = "test_project"


def test_get_dropdowns_success(mock_constants_conn):
    handler = UIServiceHandler(project_id=test_project)
    handler.constants_conn = mock_constants_conn

    result = handler.get_dropdowns(["type1", "type2"])
    expected = {"type1": ["item1", "item2"], "type2": ["item3", "item4"]}
    assert result == expected


def test_get_dropdowns_no_data(mock_constants_conn):
    mock_constants_conn.get_constants_by_types.return_value = []
    handler = UIServiceHandler(project_id=test_project)
    handler.constants_conn = mock_constants_conn

    result = handler.get_dropdowns(["type1"])
    assert result == {}


def test_get_dropdowns_key_error(mock_constants_conn):
    mock_constants_conn.get_constants_by_types.side_effect = KeyError
    handler = UIServiceHandler(project_id=test_project)
    handler.constants_conn = mock_constants_conn

    with pytest.raises(NotImplementedError):
        handler.get_dropdowns(["type1"])


def test_get_dependant_dropdown_plugin_success(mock_constants_conn):
    mock_constants_conn.get_constants_by_types.return_value = [
        {"content_type": "dependantRegistrationTypes", "data": {"parent1": ["child1", "child2"]}}
    ]
    handler = UIServiceHandler(project_id=test_project)
    handler.constants_conn = mock_constants_conn

    result = handler.get_dependant_dropdown_plugin("parent1")
    expected = ["child1", "child2"]
    assert result == expected


def test_get_dependant_dropdown_plugin_no_data(mock_constants_conn):
    mock_constants_conn.get_constants_by_types.return_value = []
    handler = UIServiceHandler(project_id=test_project)
    handler.constants_conn = mock_constants_conn

    result = handler.get_dependant_dropdown_plugin("parent1")
    expected = None
    assert result == expected


def test_update_constants_success(mock_constants_conn):
    handler = UIServiceHandler(project_id=test_project)
    handler.constants_conn = mock_constants_conn

    handler.update_constants("type1", {"key": "value"})
    mock_constants_conn.update_constants_by_type.assert_called_once_with("type1", {"key": "value"})

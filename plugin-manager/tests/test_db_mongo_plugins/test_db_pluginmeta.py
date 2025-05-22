import pytest
from unittest.mock import patch, MagicMock
from scripts.db.mongo.plugins.plugin_meta import PluginMeta
from scripts.db.schemas import PluginMetaDBSchema

PLUGIN_ID = "test_plugin_id"
PLUGIN_ID_1 = "test_plugin_id_1"
PLUGIN_ID_2 = "test_plugin_id_2"
INDUSTRY = ["test_industry"]
STATUS_ACTIVE = "active"
STATUS_RUNNING = "running"
STATUS_STOPPED = "stopped"
ERROR_MESSAGE = "test_error"
PLUGIN_DATA = {
    "plugin_id": PLUGIN_ID,
    "industry": INDUSTRY,
    "status": STATUS_ACTIVE,
    "name": "Test Plugin",
    "plugin_type": "test_type",
    "registration_type": "test_registration",
    "information": {"key": "value"},
}
MOCK_PLUGINS_LIST = [
    {"plugin_id": PLUGIN_ID_1, "industry": ["test_industry_1"], "status": STATUS_RUNNING},
    {"plugin_id": PLUGIN_ID_2, "industry": ["test_industry_2"], "status": STATUS_STOPPED},
]


@pytest.fixture
def mock_plugin_meta():
    with patch("scripts.db.schemas.PluginMetaDBSchema") as MockSchema:
        MockSchema.return_value = PluginMetaDBSchema(**PLUGIN_DATA)
        yield MockSchema


@pytest.fixture
def plugin_meta_instance():
    with patch("scripts.db.mongo.plugins.plugin_meta.mongo_client") as MockMongoClient:
        MockMongoClient.return_value = MagicMock()
        yield PluginMeta()


def test_create_plugin(plugin_meta_instance):
    with patch.object(plugin_meta_instance, "update_one") as mock_update_one:
        plugin_meta_instance.create_plugin(PLUGIN_ID, PLUGIN_DATA)
        mock_update_one.assert_called_once_with(query={"plugin_id": PLUGIN_ID}, data=PLUGIN_DATA, upsert=True)


def test_update_plugin(plugin_meta_instance):
    with patch.object(plugin_meta_instance, "update_one") as mock_update_one:
        mock_update_one.return_value.modified_count = 1
        data = {"status": "inactive"}
        plugin_meta_instance.update_plugin(PLUGIN_ID, data)
        mock_update_one.assert_called_once_with(query={"plugin_id": PLUGIN_ID}, data=data)
        assert mock_update_one.return_value.modified_count == 1


def test_get_errors(plugin_meta_instance):
    with patch.object(
        plugin_meta_instance, "find_one", return_value={"errors": ERROR_MESSAGE, "plugin_id": PLUGIN_ID}
    ) as mock_find_one:
        errors = plugin_meta_instance.get_errors(PLUGIN_ID)
        assert errors == {"errors": ERROR_MESSAGE, "plugin_id": PLUGIN_ID}
        mock_find_one.assert_called_once_with(
            query={"plugin_id": PLUGIN_ID}, filter_dict={"_id": 0, "errors": 1, "plugin_id": 1}
        )


def test_delete_plugin(plugin_meta_instance):
    with patch.object(plugin_meta_instance, "delete_many", return_value=MagicMock(deleted_count=1)) as mock_delete_many:
        deleted_count = plugin_meta_instance.delete_plugin(PLUGIN_ID)
        assert deleted_count == 1
        mock_delete_many.assert_called_once_with({"plugin_id": PLUGIN_ID})


def test_get_all_count(plugin_meta_instance):
    with patch.object(plugin_meta_instance, "count_documents", return_value=10) as mock_count_documents:
        filters = {"status": STATUS_RUNNING}
        count = plugin_meta_instance.get_all_count(filters)
        assert count == 10
        mock_count_documents.assert_called_once_with(filters)


def test_get_plugins_dict(plugin_meta_instance):
    with patch.object(plugin_meta_instance, "find", return_value=MOCK_PLUGINS_LIST) as mock_find:
        plugin_id_list = [PLUGIN_ID_1, PLUGIN_ID_2]
        plugins_dict = plugin_meta_instance.get_plugins_dict(plugin_id_list)
        assert len(plugins_dict) == 2
        assert PLUGIN_ID_1 in plugins_dict
        assert PLUGIN_ID_2 in plugins_dict
        mock_find.assert_called_once_with(query={"plugin_id": {"$in": plugin_id_list}, "status": STATUS_RUNNING})

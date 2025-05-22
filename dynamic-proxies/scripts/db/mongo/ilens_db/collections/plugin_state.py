from scripts.constants import CollectionNames, DatabaseNames
from scripts.utils.mongo_util import MongoCollectionBaseClass


class PluginState(MongoCollectionBaseClass):
    def __init__(self, mongo_client):
        super().__init__(
            mongo_client=mongo_client,
            database=DatabaseNames.ilens_configuration,
            collection=CollectionNames.plugin_state,
        )

    def get_plugin_state(self, app_name, app_id):
        return self.find_one({"app_name": app_name, "app_id": app_id})

    def create_plugin_state(self, data):
        return self.insert_one(data)

    def delete_plugin_state(self, app_name, app_id):
        return self.delete_one({"app_name": app_name, "app_id": app_id})

    def update_plugin_state(self, app_name, app_id, data):
        return self.update_one(query={"app_name": app_name, "app_id": app_id}, data=data)

    def get_plugin_by_id(self, app_id):
        return self.find_one({"app_id": app_id})

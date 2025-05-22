from typing import Any

from scripts.db.mongo.ilens_configurations.collections.constants import Constants


class UIServiceHandler:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.constants_conn = Constants()

    def get_dropdowns(self, elements: list, portal: bool = False):
        try:
            data = list(self.constants_conn.get_constants_by_types(content_types=elements))
            response = {}
            if data:
                for content in data:
                    content_type = content["content_type"]
                    content_data = content["data"]
                    if portal and content_type == "pluginTypes":
                        content_data = [item for item in content_data if item.get("value") not in ["protocols"]]
                    response[content_type] = content_data
            return response
        except KeyError:
            raise NotImplementedError

    def get_dependant_dropdown_plugin(self, parent: str, portal: bool = False):
        if data := self.constants_conn.get_constants_by_types(content_types=["dependantRegistrationTypes"]):
            data = list(data)
            result = data[0]["data"].get(parent)
            if result and portal:
                result = [item for item in result if item.get("value") != "plugin_artifact"]
            return result

    def update_constants(self, content_type: str, data: Any):
        self.constants_conn.update_constants_by_type(content_type, data)

import json
import logging
import logging as log
import time
import shutil

import shortuuid
from ut_security_util import MetaInfoSchema

from scripts.config import PathConf
from scripts.db import PluginMeta
from scripts.db.mongo.ilens_plugin.custom_apps_plugin import CustomAppsPlugin
from scripts.db.schemas import CustomAppPluginSchema, PluginMetaDBSchema
from scripts.errors import ProxyKeyNotFoundError

from . import DeploymentEngineMixin


class DeploymentEngine(DeploymentEngineMixin):
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.plugin_db_conn = PluginMeta(project_id=self.project_id)
        self.custom_app_db_conn = CustomAppsPlugin(project_id=self.project_id)

    def register(self, plugin_data: PluginMetaDBSchema, user_details: MetaInfoSchema):
        try:
            db_data = plugin_data
            if not db_data.proxy:
                raise ProxyKeyNotFoundError("Proxy Key is missing in the Plugin Meta Data.")

            custom_app_id = None
            if custom_app_data := self.custom_app_db_conn.fetch_custom_app_plugin(db_data.plugin_id):
                custom_app_id = custom_app_data.get("custom_app_id")
            custom_app_data = CustomAppPluginSchema(
                project_id=self.project_id,
                plugin_id=db_data.plugin_id,
                custom_app_id=custom_app_id or shortuuid.uuid(),
                app_name=db_data.name,  # Plugin Name
                installed_by=user_details.user_id,
                installed_on=int(time.time() * 1000),
                version=db_data.version,
                base_proxy=db_data.proxy,
                meta=self.fetch_meta(plugin_data.plugin_id),
            )
            custom_app_data.meta["files"] = None
            print(custom_app_data.model_dump())
            if self.custom_app_db_conn.update_custom_app_plugin(
                custom_app_data.plugin_id, custom_app_data.model_dump()
            ):
                logging.debug("Custom App Plugin Created")

        except ProxyKeyNotFoundError as e:
            raise e
        except Exception as e:
            log.error(f"Exception occurred in the register due to {str(e)}")

    @staticmethod
    def fetch_meta(plugin_id) -> dict:
        try:
            with open(PathConf.TEMP_PATH / f"{plugin_id}.json") as f:
                plugin_config = json.loads(f.read())
            shutil.copyfile(PathConf.TEMP_PATH / f"{plugin_id}.json", PathConf.LOCAL_IMAGE_PATH / f"{plugin_id}.json")
            plugin_config["files"] = None
            return plugin_config or {}
        except Exception as e:
            logging.exception(f"Unable to fetch widget config during registration, {e}")
            return {}

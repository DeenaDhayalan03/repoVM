import json
import logging as log
import time
import shutil

import shortuuid
from ut_security_util import MetaInfoSchema

from scripts.config import PathConf
from scripts.db import PluginMeta
from scripts.db.mongo.ilens_plugin.formio_components_plugin import FormioComponentPlugin
from scripts.db.schemas import FormioComponentPluginSchema, PluginMetaDBSchema
from scripts.errors import ProxyKeyNotFoundError

from . import DeploymentEngineMixin


class DeploymentEngine(DeploymentEngineMixin):
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.plugin_db_conn = PluginMeta(project_id=self.project_id)
        self.formio_component_db_conn = FormioComponentPlugin(project_id=self.project_id)

    def register(self, plugin_data: PluginMetaDBSchema, user_details: MetaInfoSchema):
        try:
            db_data = plugin_data
            if not db_data.proxy:
                raise ProxyKeyNotFoundError("Proxy Key is missing in the Plugin Meta Data.")

            log.debug(f"FormioComponentPluginSchema ---> {db_data.model_dump()}")
            formio_component_id = None
            if formio_component_data := self.formio_component_db_conn.fetch_formio_component_plugin(db_data.plugin_id):
                formio_component_id = formio_component_data.get("formio_component_id")
            formio_component_data = FormioComponentPluginSchema(
                project_id=self.project_id,
                plugin_id=db_data.plugin_id,
                formio_component_id=formio_component_id or shortuuid.uuid(),
                component_name=db_data.name,  # Plugin Name
                installed_by=user_details.user_id,
                installed_on=int(time.time() * 1000),
                version=db_data.version,
                base_proxy=db_data.proxy,
                meta=self.fetch_meta(plugin_data.plugin_id),
            )
            formio_component_data.meta["files"] = None
            resp = self.formio_component_db_conn.update_formio_component_plugin(
                formio_component_data.plugin_id, formio_component_data.model_dump()
            )
            print(f"Formio Component Plugin Created {formio_component_data.model_dump()}")
            if resp:
                log.debug("Formio Component Plugin Created")

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
            log.exception(f"Unable to fetch widget config during registration, {e}")
            return {}

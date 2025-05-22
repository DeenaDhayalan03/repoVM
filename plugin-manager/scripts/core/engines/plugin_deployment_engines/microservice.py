import logging as log

from ut_security_util import MetaInfoSchema

from scripts.db import PluginMeta
from scripts.db.schemas import PluginMetaDBSchema
from scripts.errors import ProxyKeyNotFoundError

from . import DeploymentEngineMixin


class DeploymentEngine(DeploymentEngineMixin):
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.plugin_db_conn = PluginMeta(project_id=self.project_id)

    def register(self, plugin_data: PluginMetaDBSchema, user_details: MetaInfoSchema):
        try:
            db_data = plugin_data
            if not db_data.proxy:
                raise ProxyKeyNotFoundError("Proxy Key is missing in the Plugin Meta Data.")

            log.debug(f"MicroservicePluginSchema ---> {db_data.model_dump()}")

        except ProxyKeyNotFoundError as e:
            raise e
        except Exception as e:
            log.error(f"Exception occurred in the register due to {str(e)}")

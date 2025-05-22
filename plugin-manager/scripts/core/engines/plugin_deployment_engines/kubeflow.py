import logging as log

from ut_security_util import MetaInfoSchema

from scripts.db import PluginMeta
from scripts.db.schemas import PluginMetaDBSchema

from . import DeploymentEngineMixin


class DeploymentEngine(DeploymentEngineMixin):
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.plugin_db_conn = PluginMeta(project_id=self.project_id)

    def register(self, plugin_data: PluginMetaDBSchema, user_details: MetaInfoSchema):
        try:
            db_data = plugin_data
            log.info(f"Kubeflow Plugin registered with name: {db_data.name}")
            log.debug(f"KubeflowPluginSchema ---> {db_data.model_dump()}")

        except Exception as e:
            log.error(f"Exception occurred in the register due to {str(e)}")

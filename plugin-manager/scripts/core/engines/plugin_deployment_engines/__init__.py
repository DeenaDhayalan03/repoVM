from abc import ABC, abstractmethod

from ut_security_util import MetaInfoSchema

from scripts.db.schemas import PluginMetaDBSchema


class DeploymentEngineMixin(ABC):
    @abstractmethod
    def register(self, plugin_data: PluginMetaDBSchema, user_details: MetaInfoSchema): ...

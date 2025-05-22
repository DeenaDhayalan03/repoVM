import json
import logging
import time
import shutil

import shortuuid
from ut_security_util import MetaInfoSchema

from scripts.config import PathConf, Services
from scripts.constants.api import ExternalAPI
from scripts.db import PluginMeta
from scripts.db.mongo.ilens_widget.aggregation import AggregationsWidget
from scripts.db.mongo.ilens_widget.widget_plugin import WidgetPlugins
from scripts.db.schemas import PluginMetaDBSchema, WidgetPluginSchema
from scripts.errors import ProxyKeyNotFoundError
from scripts.utils.common_util import hit_external_service

from . import DeploymentEngineMixin


class DeploymentEngine(DeploymentEngineMixin):
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.plugin_db_conn = PluginMeta(project_id=self.project_id)
        self.widget_db_conn = WidgetPlugins(project_id=self.project_id)

    def register(self, plugin_data: PluginMetaDBSchema, user_details: MetaInfoSchema):
        try:
            db_data = plugin_data
            if not db_data.proxy:
                raise ProxyKeyNotFoundError("Proxy Key is missing in the Plugin Meta Data.")
            widget_pl_id = None
            if widget_data := self.widget_db_conn.fetch_widget_plugin(db_data.plugin_id):
                widget_pl_id = widget_data.get("widget_pl_id")
            widget_data = WidgetPluginSchema(
                project_id=self.project_id,
                plugin_id=db_data.plugin_id,
                widget_pl_id=widget_pl_id or shortuuid.uuid(),
                chart_type=db_data.name,  # Plugin Name
                installed_by=user_details.user_id,
                installed_on=int(time.time() * 1000),
                version=db_data.version,
                proxy=db_data.proxy,
                data_source=db_data.information.get("data_source", []),
                category=db_data.information.get("category", ""),
                widget_type=db_data.information.get("widget_type", []),
                widget_category=db_data.information.get("widget_page_category", None),
                enable_plugin_report=db_data.information.get("enable_plugin_report", False),
                meta=self.fetch_meta(plugin_data.plugin_id),
            )
            widget_data.meta["files"] = None
            if self.widget_db_conn.update_widget_plugin(widget_data.plugin_id, widget_data.model_dump()):
                logging.debug("Widget Plugin Created")

        except ProxyKeyNotFoundError as e:
            raise e
        except Exception as e:
            logging.error(f"Exception occurred in the register due to {str(e)}")

    @staticmethod
    def get_plugin_details(api, meta: MetaInfoSchema):
        try:
            return hit_external_service(api_url=api, method="get", request_cookies=meta.model_dump(by_alias=True))
        except ModuleNotFoundError:
            return {}
        except Exception as e:
            logging.error(e)
            return {}

    def save_meta_data(self, plugin_id, cookies):
        """Deprecated: Widget configuration loaded during registration"""
        try:
            widget_plugin_data = {}
            if widget_plugin := list(
                self.widget_db_conn.get_aggregated_query_data(
                    AggregationsWidget.get_widget_plugins_agg_query(self.project_id, plugin_id)
                )
            ):
                widget_plugin_data = widget_plugin[0]
            proxy = widget_plugin_data.get("proxy")
            widget_pl_id = widget_plugin_data.get("widget_pl_id")
            if not proxy:
                logging.debug("Skipping as no proxy added")
                return
            api = f"{Services.HOME_LINK}{proxy}{ExternalAPI.api_load_configurations}"
            config = self.get_plugin_details(api, cookies)

            if self.widget_db_conn.update_widget_id(widget_pl_id, {"meta": config}):
                logging.debug("Widget Plugin Meta Info Stored Successfully")
                return True

        except Exception as e:
            logging.error(f"Error occurred in the save meta data due to {str(e)}")
            return False

    @staticmethod
    def fetch_meta(plugin_id) -> dict:
        try:
            with open(PathConf.TEMP_PATH / f"{plugin_id}.json") as f:
                widget_config = json.loads(f.read())
            shutil.copyfile(PathConf.TEMP_PATH / f"{plugin_id}.json", PathConf.LOCAL_IMAGE_PATH / f"{plugin_id}.json")
            widget_config["files"] = None
            return widget_config or {}
        except Exception as e:
            logging.exception(f"Unable to fetch widget config during registration, {e}")
            return {}

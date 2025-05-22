import logging
import os
import pathlib
import shutil
from copy import deepcopy
from io import BytesIO
from datetime import datetime
from pathlib import Path
from docker.errors import NotFound
import numpy as np
import pandas as pd
from fastapi import BackgroundTasks, UploadFile, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from ut_security_util import MetaInfoSchema

from scripts.config import ExternalServices, MinioSettings, PathConf, Services
from scripts.constants import (
    delete_container_support,
    git_access_token_mask,
    job_types,
    plugin_redeployment_required,
)
from scripts.constants.api import APIEndPoints, ExternalAPI
from scripts.constants.ui_components import (
    create_new_button,
    plugin_code_scans_header_content,
    plugin_list_table_actions,
    plugin_list_table_header,
    plugin_list_table_actions_for_portal,
    plugin_list_table_header_for_portal,
)
from scripts.db import PluginMeta, VulnerablityScanReport
from scripts.db.mongo.ilens_asset_model.collections.industry_category import (
    IndustryCategory,
)
from scripts.db.mongo.ilens_configurations.lookup_table import Lookups
from scripts.db.mongo.ilens_plugin.custom_apps_plugin import CustomAppsPlugin
from scripts.db.mongo.ilens_plugin.formio_components_plugin import FormioComponentPlugin
from scripts.db.mongo.ilens_widget.widget_plugin import WidgetPlugins
from scripts.db.schemas import PluginFetchResponse, PluginMetaDBSchema
from scripts.utils.notification_util import push_notification, push_notification_docker_download
from scripts.utils.docker_util import DockerUtil
from scripts.errors import ContentTypeError, PluginAlreadyExistError, PluginNotFoundError
from scripts.services.v1.handler.deployment import DeploymentHandler
from scripts.services.v1.schemas import Plugin, PluginListRequest, DefaultResponse
from scripts.utils.common_util import get_unique_id, hit_external_service
from scripts.utils.external_services import delete_container
from scripts.utils.minio_util import MinioUtility
from scripts.config import AzureCredentials
from scripts.utils.notification_util import NotificationSchema, NotificationSchemaDownload

DEPLOYED = "Deployed - Running"
SCAN_SUCCESSFUL = "Scan Successful"


class PluginHandler:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.plugin_db_conn = PluginMeta(project_id=project_id)
        self.widget_plugins = WidgetPlugins(project_id)
        self.custom_app_db_conn = CustomAppsPlugin(project_id=project_id)
        self.formio_component_db_conn = FormioComponentPlugin(project_id=project_id)
        self.docker_util = DockerUtil()

    def _name_validation(self, plugin_name: str) -> bool:
        query = {"name": plugin_name}
        matched_count = self.plugin_db_conn.get_all_count(filters=query)
        return matched_count > 0

    def create_plugin(self, plugin_data: Plugin, bg_task: BackgroundTasks, rbac_permissions: dict):  # NOSONAR
        existing_plugin = self.plugin_db_conn.fetch_plugin(plugin_id=plugin_data.plugin_id, version=plugin_data.version)

        if existing_plugin and existing_plugin.plugin_id != plugin_data.plugin_id:
            raise PluginAlreadyExistError(
                f"A plugin with the name {plugin_data.name} already exists with a different plugin ID."
            )
        if plugin_data.advancedConfiguration:
            self.resource_validation(plugin_data.advancedConfiguration.bodyContent)
        _plugin_data = plugin_data.model_dump()
        if existing_plugin:
            is_update = True
        else:
            is_update = False
            if not rbac_permissions.get("create"):
                raise PermissionError("Permission denied to create plugin")
        plugin_id = plugin_data.plugin_id or get_unique_id()
        _plugin_data["plugin_id"] = plugin_id
        db_data = PluginMetaDBSchema(**_plugin_data)
        if db_data.plugin_type == "kubeflow":
            db_data.deploy_as_container = False
        data = db_data.model_dump(exclude_none=True)
        if not is_update:
            data["deployment_status"] = "pending"
            data["deployed_by"] = None
            data["deployed_on"] = None
        if data.get("git_access_token", None) and data["git_access_token"] == git_access_token_mask:
            del data["git_access_token"]
        if is_update:
            if "version" in data:
                del data["version"]
            plugin_db_data = self.plugin_db_conn.fetch_plugin(plugin_id=plugin_id, version=plugin_data.version)
            if self.plugin_redeploy_validator(plugin_data.model_dump(), plugin_db_data.model_dump()):
                logging.info(f"Plugin redeployment required: {plugin_data.name}-{plugin_data.plugin_id}")
                _plugin_data["deployment_status"] = "pending"
                bg_task.add_task(delete_container, plugin_db_data.name, plugin_db_data.plugin_id)
            else:
                _plugin_data["deployment_status"] = plugin_db_data.deployment_status

            self.plugin_db_conn.update_plugin(plugin_id=plugin_id, data=data, version=plugin_data.version)
        else:
            self.plugin_db_conn.create_plugin(plugin_id=plugin_id, data=data, version=plugin_data.version)
        if "current_version" in _plugin_data:
            self.plugin_db_conn.update_many(
                {"plugin_id": plugin_id}, {"current_version": _plugin_data["current_version"]}, upsert=False
            )

        return plugin_id

    def list_plugins(self, list_request: PluginListRequest) -> dict[str, list]:
        required_fields = self._get_required_fields(list_request.tz)
        raw_data = list(self.plugin_db_conn.list_plugin_ag_grid(list_request, additional_projection=required_fields))
        plugin_records = self._group_plugins_by_id(raw_data)
        filtered_data = self._filter_plugin_records(plugin_records, list_request.records)
        data = self.data_formatter(filtered_data, portal=list_request.portal) if filtered_data else []
        end_of_records = len(filtered_data) < list_request.records
        return {
            "bodyContent": data,
            "total_no": self.plugin_db_conn.get_counts_ag_grid(list_request),
            "endOfRecords": end_of_records,
        }

    def _get_required_fields(self, timezone: str) -> dict:
        required_fields = {i["key"]: 1 for i in plugin_list_table_header["headerContent"]}
        required_fields["deployment_status"] = 1
        required_fields.pop("plugin_status", None)
        required_fields["plugin_id"] = 1
        required_fields["_id"] = 0

        required_fields["deployed_on"] = {
            "$dateToString": {
                "format": "%d/%m/%Y %H:%M:%S",
                "date": "$deployed_on",
                "timezone": timezone,
            }
        }
        required_fields["disabledActions"] = 1
        return required_fields

    def _group_plugins_by_id(self, raw_data: list) -> dict:
        plugin_records = {}
        for record in raw_data:
            plugin_id = record["plugin_id"]
            if plugin_id not in plugin_records:
                plugin_records[plugin_id] = []
            plugin_records[plugin_id].append(record)
        return plugin_records

    def _filter_plugin_records(self, plugin_records: dict, record_limit: int) -> list:
        filtered_data = []
        for records in plugin_records.values():
            if len(records) == 1:
                filtered_data.append(records[0])
            else:
                for record in records:
                    if record.get("current_version") == record.get("version"):
                        filtered_data.append(record)
                        break
                else:
                    filtered_data.append(records[0])
        return filtered_data[:record_limit]

    def determine_disabled_actions(self, plugin_id: str) -> list:
        plugin = self.plugin_db_conn.find_one(
            {"plugin_id": plugin_id},
            {"deployment_status": 1, "plugin_type": 1, "current_version": 1, "_id": 0},
        )
        if not plugin or "deployment_status" not in plugin:
            return []

        current_version = plugin.get("current_version")
        if current_version:
            plugin = self.plugin_db_conn.find_one(
                {"plugin_id": plugin_id, "version": current_version},
                {"deployment_status": 1, "plugin_type": 1, "_id": 0},
            )

        deployment_status = plugin["deployment_status"].lower()
        disabled_actions = []
        added_actions = set()

        def add_action(action):
            if action not in added_actions:
                disabled_actions.append(action)
                added_actions.add(action)

        if deployment_status not in ["deploying", "running"]:
            add_action("artifact_download")
        if deployment_status == "running":
            add_action("start")
        elif deployment_status in ["pending", "deploying", "scanning", "failed"]:
            add_action("start")
            add_action("pause")
        elif deployment_status == "stopped":
            add_action("pause")
            add_action("logs")

        plugin_type = plugin.get("plugin_type", "").lower()
        if plugin_type in ["kubeflow", "protocols"]:
            add_action("start")
            add_action("pause")

        return disabled_actions

    def determine_plugin_status(self, row, portal_key=False):
        current_version = row.get("version")
        if row["deployment_status"] == "Failed":
            return self._handle_failed_status(row, portal_key, current_version)
        elif row["deployment_status"] in ["Running", "Stopped"]:
            return self._handle_running_or_paused_status(row, portal_key)
        else:
            return self._handle_other_status(row, current_version)

    def _handle_failed_status(self, row, portal_key, current_version):
        status = self.fetch_status_from_db(row["plugin_id"], current_version)
        if portal_key:
            return {"color": "#ff0000", "status": "Scan Failed"}
        if status == "running":
            return {"color": "#ff0000", "status": "Failed"}
        return {"color": "#ff0000", "status": status or "Failed"}

    def _handle_running_or_paused_status(self, row, portal_key):
        if portal_key and row["plugin_type"] == "Kubeflow":
            return {"status": SCAN_SUCCESSFUL, "color": "#008000", "portal": True}
        if row["deployment_status"] == "Stopped":
            return {"color": "#C3C4CA", "status": "Stopped"}
        return {"color": "#008000", "status": DEPLOYED}

    def _handle_other_status(self, row, current_version):
        status = self.fetch_status_from_db(row["plugin_id"], current_version)
        if status == "Deployed":
            return {"status": DEPLOYED, "color": "#008000"}
        elif row["deployment_status"] == "Pending":
            return {"status": "Pending", "process": "In Progress", "color": "#F29339"}
        elif status in [SCAN_SUCCESSFUL, SCAN_SUCCESSFUL]:
            return {"status": status, "color": "#008000", "portal": True}
        else:
            return {"status": status, "process": "In Progress", "color": "#F29339"}

    def data_formatter(self, _data, portal=False):
        data_df = pd.DataFrame.from_records(_data)
        data_df["plugin_type"] = data_df["plugin_type"].apply(
            lambda x: " ".join([word.capitalize() for word in x.split("_")])
        )
        data_df.loc[data_df["deployment_status"] == "success", "deployment_status"] = "running"
        data_df["download"] = data_df["deployment_status"].apply(lambda status: status == "RUNNING")
        data_df["deployment_status"] = data_df["deployment_status"].str.capitalize()
        data_df.loc[data_df["deployment_status"] == "Paused", "deployment_status"] = "Stopped"

        data_df["plugin_status"] = data_df.apply(self.determine_plugin_status, axis=1, portal_key=portal)
        data_df["plugin_status_color"] = data_df["plugin_status"].apply(lambda x: x["color"])
        data_df["plugin_status"] = data_df["plugin_status"].apply(lambda x: x["status"])

        data_df["deployed_on"] = data_df.apply(
            lambda row: self.format_deployed_on(row["deployed_on"], row["plugin_status"]), axis=1
        )
        data_df["disabledActions"] = data_df["plugin_id"].apply(self.determine_disabled_actions)
        data_df = data_df.replace({pd.NaT: None, np.nan: None})

        if portal:
            data_df = data_df.drop(columns=["deployment_status"])

        return data_df.to_dict("records")

    def format_deployed_on(self, deployed_on, status):
        if (status == DEPLOYED or status == SCAN_SUCCESSFUL) and deployed_on:
            try:
                date_obj = datetime.strptime(deployed_on, "%d/%m/%Y %H:%M:%S")
                return date_obj.strftime("%d %b %Y")
            except ValueError:
                return "-"
        return "-"

    def fetch_status_from_db(self, plugin_id, current_version):
        plugin = self.plugin_db_conn.find_one(
            {"plugin_id": plugin_id, "version": current_version}, {"status": 1, "_id": 0}
        )
        return plugin.get("status", None)

    def save_configurations(self, plugin_id: str, configurations: dict):
        self.plugin_db_conn.update_plugin(plugin_id=plugin_id, data={"configurations": configurations})

    def upload_files(
        self,
        plugin_id: str,
        files: list[UploadFile],
    ):
        store_path = PathConf.CODE_STORE_PATH / plugin_id / "uploads"
        plugin = self.plugin_db_conn.find_one(query={"plugin_id": plugin_id}, filter_dict={"plugin_type": 1, "_id": 0})
        if plugin.get("plugin_type", "") == "widget":
            logging.info("Deleting exisitng widget thumbnail")
            shutil.rmtree(store_path, ignore_errors=True)
        store_path.mkdir(parents=True, exist_ok=True)
        for file in files:
            f_path = store_path / file.filename
            try:
                with open(f_path, "wb") as f:
                    while contents := file.file.read(1024 * 1024):
                        f.write(contents)
                        logging.info(f"Uploading file: {file.filename}")
            except Exception as e:
                raise RuntimeError("Error occurred while saving the file") from e
            finally:
                file.file.close()
        self.plugin_db_conn.update_plugin(plugin_id=plugin_id, data={"file_upload_path": str(store_path)})

    def get_uploaded_files(self, plugin_id: str):
        plugin_data = self.plugin_db_conn.fetch_plugin(
            plugin_id,
            additional_filters=[
                {"file_upload_path": {"$ne": None}},
                {"file_upload_path": {"$exists": "true"}},
            ],
        )
        if not plugin_data:
            raise PluginNotFoundError
        if plugin_data.file_upload_path:
            f_path = pathlib.Path(plugin_data.file_upload_path)
            return [i.name for i in f_path.iterdir() if i.is_file()]
        return []

    def download_uploaded_files(self, plugin_id: str, file_name):
        plugin_data = self.plugin_db_conn.fetch_plugin(
            plugin_id,
            additional_filters=[
                {"file_upload_path": {"$ne": None}},
                {"file_upload_path": {"$exists": "true"}},
            ],
        )
        if not plugin_data:
            raise PluginNotFoundError
        dir_path = pathlib.Path(plugin_data.file_upload_path)
        f_path = dir_path / file_name
        return FileResponse(f_path)

    def get_plugin(self, plugin_id: str, version: float) -> dict | None:
        data = self.plugin_db_conn.fetch_plugin(plugin_id=plugin_id, version=version)
        if not data.current_version:
            data.current_version = data.version
        if not data:
            return None
        if data.plugin_type in job_types and data.plugin_type != "kubeflow" and data.configurations:
            data.configurations = self.process_configurations_when_fetched(data.configurations)

        if data and data.git_access_token:
            data.git_access_token = git_access_token_mask
        return PluginFetchResponse(**data.model_dump()) if data else None

    def delete_plugin(self, plugin_id: str, user_details: MetaInfoSchema, bg_task: BackgroundTasks):
        if not (plugin_data := self.plugin_db_conn.fetch_plugin(plugin_id)):
            raise PluginNotFoundError(f"Plugin ID {plugin_id} not found")
        self.plugin_db_conn.delete_plugin(plugin_id=plugin_id)
        if plugin_data.registration_type == "bundle_upload" and plugin_data.minio_file_path:
            MinioUtility(
                endpoint=MinioSettings.MINIO_ENDPOINT,
                access_key=MinioSettings.MINIO_ACCESS_KEY,
                secret_key=MinioSettings.MINIO_SECRET_KEY,
                secure=MinioSettings.MINIO_SECURE,
            ).delete_object(MinioSettings.MINIO_BUCKET_NAME, plugin_data.minio_file_path)

        if plugin_data.plugin_type in delete_container_support:
            if plugin_data.plugin_type == "widget":
                logging.info(f"Delete existing widget plugin version: {plugin_data.name}-{plugin_data.plugin_id}")
                self.widget_plugins.remove_widget_plugin(plugin_id)
            elif plugin_data.plugin_type == "custom_app":
                logging.info(f"Delete existing custom app plugin version: {plugin_data.name}-{plugin_data.plugin_id}")
                self.custom_app_db_conn.remove_custom_app_plugin(plugin_id)
            elif plugin_data.plugin_type == "formio_component":
                logging.info(
                    f"Delete existing formio component plugin version: {plugin_data.name}-{plugin_data.plugin_id}"
                )
                self.formio_component_db_conn.remove_formio_component_plugin(plugin_id)
            shutil.rmtree(PathConf.LOCAL_IMAGE_PATH / f"{plugin_id}.json", ignore_errors=True)
            bg_task.add_task(delete_container, plugin_data.name, plugin_id)
        elif plugin_data.plugin_type == "kubeflow":
            bg_task.add_task(
                DeploymentHandler(project_id=user_details.project_id).delete_kubeflow_pipeline,
                plugin_data.name,
                user_details,
            )

    def get_errors(self, plugin_id: str):
        return self.plugin_db_conn.get_errors(plugin_id=plugin_id)

    def get_info(self, plugin_id: str, version: float, host: str = "") -> dict:
        data = self.plugin_db_conn.fetch_plugin(plugin_id=plugin_id, version=version)
        if not data:
            raise PluginNotFoundError(f"Plugin ID {plugin_id} not found")
        title = data.name
        info_list = [
            {"label": "Plugin type", "value": data.plugin_type},
            {"label": "Version", "value": data.version},
        ]

        industry_category_conn = IndustryCategory()
        if data.industry:
            industry = [
                industry_category_conn.get_industry_name_by_id(industry_category_id=industry_id)
                for industry_id in data.industry
            ]
            industry = ", ".join(industry)
            info_list.append(
                {
                    "label": "Industry",
                    "value": industry,
                }
            )

        if data.git_url:
            info_list.append({"label": "Git URL", "value": data.git_url})
        if data.file_upload_path:
            info_list.append({"label": "File Upload Path", "value": data.file_upload_path})
        if data.proxy:
            info_list.append({"label": "Proxy", "value": data.proxy})
        if host and data.proxy:
            info_list.extend([{"label": "URL", "value": host + data.proxy}])
        if data.additional_fields:
            info_list.extend(data.additional_fields)

        return {"info": info_list, "title": title}

    def get_plugin_logs(self, plugin_id: str, version: float) -> str | None:
        if plugin := self.plugin_db_conn.fetch_plugin(plugin_id=plugin_id, version=version):
            logging.info(f"Fetching logs for plugin: {plugin.name}-{plugin_id}")
            resp = hit_external_service(
                api_url=f"{ExternalServices.PROXY_MANAGER_URL}{ExternalAPI.plugin_logs}",
                params={"plugin": f"{plugin.name}-{plugin_id}".replace("_", "-").lower()},
            )
            plugin.errors.append(resp.get("data"))
            return "\n".join(plugin.errors)
        return None

    def download_plugin_logs(self, plugin_id: str):
        if plugin := self.plugin_db_conn.fetch_plugin(plugin_id=plugin_id):
            logging.info(f"Getting logs for plugin: {plugin.name}-{plugin_id}")
            resp = hit_external_service(
                api_url=f"{ExternalServices.PROXY_MANAGER_URL}{ExternalAPI.plugin_logs}",
                params={"plugin": f"{plugin.name}-{plugin_id}".replace("_", "-").lower()},
            )
            plugin.errors.append(resp.get("data"))
            data = "\n".join(plugin.errors)
            data = data.replace("<br/>", "\n")
            return StreamingResponse(
                BytesIO(data.encode()),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={plugin.name}.log"},
            )
        else:
            return None

    def get_plugin_report(self, plugin_id: str) -> dict | None:
        vulnerability_scan_report = VulnerablityScanReport(project_id=self.project_id)
        if plugin_report := vulnerability_scan_report.get_report(plugin_id=plugin_id):
            return plugin_report
        else:
            return None

    def download_plugin_report(self, plugin_id: str):
        vulnerability_scan_report = VulnerablityScanReport(project_id=self.project_id)
        if plugin_report := vulnerability_scan_report.get_report(plugin_id=plugin_id):
            plugin_name = self.plugin_db_conn.fetch_plugin(plugin_id=plugin_id).name
            data = pd.DataFrame.from_records(plugin_report.get("vulnerabilities", []))
            report = BytesIO()
            writer = pd.ExcelWriter(report, engine="xlsxwriter")
            data.to_excel(writer, sheet_name="Sheet1", index=False)
            writer.close()
            report.seek(0)

            return StreamingResponse(
                report,
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={plugin_name}.xlsx"},
            )
        else:
            return None

    def get_plugin_advance_config(self):
        lookups = Lookups(project_id=self.project_id)
        lookup_data = lookups.find_one_lookup_name(lookup_name="plugin_advance_config")
        return [
            {
                "key": property.get("key"),
                "label": property.get("value").get("label"),
                "description": property.get("value").get("description"),
            }
            for property in lookup_data.get("lookup_data", [])[0].get("properties")
        ]

    @staticmethod
    def resource_validation(resources: list):
        resource_list = {resource.property: resource.input for resource in resources}
        if (
            resource_list.get("memory_request")
            and resource_list.get("memory_limit")
            and resource_list.get("memory_request") > resource_list.get("memory_limit")
        ):
            raise ValueError("Memory request should be less than limit")

        if (
            resource_list.get("cpu_request")
            and resource_list.get("cpu_limit")
            and resource_list.get("cpu_request") > resource_list.get("cpu_limit")
        ):
            raise ValueError("CPU request should be less than limit")

    @staticmethod
    def plugin_redeploy_validator(plugin_request_data: dict, plugin_db_data: dict):
        different_keys = [
            key for key in plugin_redeployment_required if plugin_request_data.get(key) != plugin_db_data.get(key)
        ]

        if plugin_request_data.get("git_access_token") == git_access_token_mask:
            different_keys.remove("git_access_token")

        elif bool(different_keys):
            return True
        return False

    def get_plugin_list_table_header_based_on_portal(self, rbac_permissions: dict, portal: bool):
        if portal:
            return self.get_plugin_list_table_header_for_portal()
        else:
            return self.get_plugin_list_table_header(rbac_permissions)

    def get_plugin_list_table_header(self, rbac_permissions: dict):
        actions = deepcopy(plugin_list_table_actions)
        for icons in actions["actions"]:
            if icons.get("action") == "edit" and not rbac_permissions.get("edit"):
                actions["actions"].remove(icons)
        if "options" in actions["actions"][-1]:
            for icons in actions["actions"][-1]["options"]:
                if icons.get("action") == "delete" and not rbac_permissions.get("delete"):
                    actions["actions"][-1]["options"].remove(icons)
        if rbac_permissions.get("create"):
            actions["externalActions"].append(create_new_button)
        return plugin_list_table_header | actions

    def get_plugin_list_table_header_for_portal(self):
        actions = deepcopy(plugin_list_table_actions_for_portal)
        return plugin_list_table_header_for_portal | actions

    def get_plugin_security_check(self, plugin_id: str, version: float):
        if plugin_data := self.plugin_db_conn.fetch_plugin(plugin_id=plugin_id, version=version):
            code_scan_report = VulnerablityScanReport(project_id=self.project_id)
            security_checks = [
                {
                    "label": "Antivirus Scan",
                    "key": "antivirus",
                    "value": plugin_data.security_checks.model_dump().get("antivirus", False),
                },
                {
                    "label": "SonarQube Scan",
                    "key": "sonarqube",
                    "value": plugin_data.security_checks.model_dump().get("sonarqube", False),
                },
                {
                    "label": "Vulnerability Scan",
                    "key": "vulnerabilities",
                    "value": (
                        True
                        if plugin_data.security_checks.model_dump().get("vulnerabilities") is None
                        and plugin_data.deployment_status == "running"
                        else plugin_data.security_checks.model_dump().get("vulnerabilities")
                    ),
                },
            ]
            if plugin_data.security_checks:
                return self._handle_security_checks(plugin_id, code_scan_report, plugin_data, security_checks)
            else:
                return {"checks": security_checks} | {
                    "fetch_logs": self.status_check(plugin_id=plugin_id, version=version)
                }
        raise PluginNotFoundError(f"Plugin ID {plugin_id} not found")

    def status_check(self, plugin_id: str, version: float) -> bool:
        plugin_data = self.plugin_db_conn.find_one({"plugin_id": plugin_id, "version": version})
        if not plugin_data:
            raise PluginNotFoundError(f"Plugin ID {plugin_id} not found")
        security_checks = plugin_data.get("security_checks", {})
        return (
            plugin_data.get("deployment_status") == "running"
            if all(
                [
                    security_checks.get("antivirus", False),
                    security_checks.get("vulnerabilities") in [None, True],
                    security_checks.get("sonarqube", False),
                ]
            )
            else False
        )

    def _handle_security_checks(
        self,
        plugin_id: str,
        code_scan_report: VulnerablityScanReport,
        plugin_data: PluginMetaDBSchema,
        security_checks: list,
    ) -> dict:
        if not (plugin_report := code_scan_report.get_report(plugin_id=plugin_id)):
            return {"checks": security_checks} | {
                "fetch_logs": self.status_check(plugin_id=plugin_id, version=plugin_data.version)
            }
        body_content = []
        header_content = {}
        for check in security_checks:
            key = check["key"]
            value = plugin_data.security_checks.model_dump().get(key, None)
            if value is None and plugin_data.deployment_status == "running" and key == "vulnerabilities":
                value = True
            check["value"] = value
            if not value and key != "vulnerabilities":  # Ensure vulnerabilities check is updated before breaking
                body_content = plugin_report.get(key, None)
                header_content = plugin_code_scans_header_content.get(key, None)
                break
        return (
            {"checks": security_checks}
            | header_content
            | {"bodyContent": body_content}
            | {"fetch_logs": self.status_check(plugin_id=plugin_id, version=plugin_data.version)}
        )

    def vulnerability_report(self, vulnerabilities) -> list:
        return [
            {
                "package": vulnerability.get("Package", None),
                "description": vulnerability.get("Description", None),
            }
            for vulnerability in vulnerabilities
        ]

    def antivirus_scan_report(self, antivirus_report: dict) -> list:
        return [
            {
                "infected_files": antivirus_report.get("Infected files"),
            }
        ]

    def sonarqube_scan_report(self, sonarqube_report: dict) -> list:
        return [
            {
                "type": records.get("type", None),
                "file": records.get("file", None),
                "severity": records.get("severity", None),
                "line": records.get("line", None),
                "message": records.get("message", None),
                "rule": records.get("rule", None),
            }
            for records in sonarqube_report
        ]

    def list_plugins_by_type(self, plugin_type: str):
        if plugin_type == "custom_app":
            query = {"plugin_type": "custom_app", "deployment_status": "running"}
            data = self.plugin_db_conn.find(query=query, filter_dict={"name": 1, "plugin_id": 1, "_id": 0})
            return [{"label": plugin["name"], "value": plugin["plugin_id"]} for plugin in data]
        elif plugin_type == "formio_component":
            query = {"plugin_type": "formio_component", "deployment_status": "running"}
            formio_plugins = self.plugin_db_conn.find(
                query=query,
                filter_dict={"plugin_id": 1, "name": 1, "_id": 0, "proxy": 1},
            )
            data = {}
            for plugin in formio_plugins:
                formio_component_data = self.formio_component_db_conn.fetch_formio_component_plugin(
                    plugin_id=plugin.get("plugin_id")
                )
                if not formio_component_data["meta"].get("files"):
                    formio_component_data["meta"]["files"] = hit_external_service(
                        api_url=f"{Services.HOME_LINK}{plugin.get('proxy')}/formio_component/load_styles",
                        method="get",
                    )["data"]
                    self.formio_component_db_conn.update_formio_component_plugin(
                        plugin_id=plugin.get("plugin_id"), data=formio_component_data
                    )
                data[f'{plugin["name"]}'] = formio_component_data["meta"] | {"base_proxy": plugin.get("proxy")}
            return data
        else:
            return {}

    def fetch_plugin_details(self, plugin_id: str) -> dict | None:
        if not (plugin_data := self.plugin_db_conn.fetch_plugin(plugin_id=plugin_id)):
            raise PluginNotFoundError(f"Plugin with {plugin_id} not found")
        if plugin_data.plugin_type == "custom_app":
            return self._fetch_custom_app_details(plugin_id)
        elif plugin_data.plugin_type == "formio_component":
            return self._fetch_formio_component_details(plugin_id)
        elif plugin_data.plugin_type == "widget":
            return self._fetch_widget_details(plugin_id)
        else:
            return None

    def _fetch_custom_app_details(self, plugin_id: str):
        app_data = self.custom_app_db_conn.fetch_custom_app_plugin(plugin_id=plugin_id)
        if not app_data["meta"].get("files"):
            app_data["meta"]["files"] = hit_external_service(
                api_url=f"{Services.HOME_LINK}{app_data['base_proxy']}/custom_app/load_styles",
                method="get",
            )["data"]
            self.custom_app_db_conn.update_custom_app_plugin(plugin_id=plugin_id, data=app_data)
        return app_data

    def _fetch_formio_component_details(self, plugin_id: str):
        formio_data = self.formio_component_db_conn.fetch_formio_component_plugin(plugin_id=plugin_id)
        if not formio_data["meta"].get("files"):
            formio_data["meta"]["files"] = hit_external_service(
                api_url=f"{Services.HOME_LINK}{formio_data['base_proxy']}/formio_component/load_styles",
                method="get",
            )["data"]
            self.formio_component_db_conn.update_formio_component_plugin(plugin_id=plugin_id, data=formio_data)
        return formio_data

    def _fetch_widget_details(self, plugin_id: str):
        widget_data = self.widget_plugins.fetch_widget_plugin(plugin_id=plugin_id)
        if not widget_data["meta"].get("files"):
            widget_data["meta"]["files"] = hit_external_service(
                api_url=f"{Services.HOME_LINK}{widget_data['proxy']}/widget/load_styles",
                method="get",
            )["data"]
            self.widget_plugins.update_widget_plugin(plugin_id=plugin_id, data=widget_data)
        return widget_data

    def fetch_plugin_env_config(self):
        options = [
            {"label": "Text", "value": "text", "options": None},
            {"label": "Secure", "value": "secure", "options": None},
        ]
        kubernetes_secrets = hit_external_service(
            api_url=f"{ExternalServices.PROXY_MANAGER_URL}{ExternalAPI.secrets}",
            method="get",
        )
        if kubernetes_secrets.get("data", None):
            options.append(
                {
                    "label": "Kubernetes Secrets",
                    "value": "kubernetes_secrets",
                    "options": [
                        {
                            "label": value.upper(),
                            "value": value,
                            "type": "kubernetes",
                        }
                        for value in kubernetes_secrets.get("data")
                    ],
                }
            )
        return options

    def process_configurations_when_fetched(self, configurations: dict | list) -> list:
        if isinstance(configurations, dict):
            return [{"key": key, "value": value, "type": "text"} for key, value in configurations.items()]
        elif isinstance(configurations, list):
            for config in configurations:
                if config["type"] == "secure":
                    config["value"] = "*" * len(config["value"])
            return configurations
        return []

    def process_configurations_when_saved(self, request_config: list, saved_config: list | dict) -> (list, bool):  # type: ignore
        is_update = False
        request_config_dict = {config["key"]: config["value"] for config in request_config}

        if isinstance(saved_config, dict):
            request_config_dict, is_update = self._process_dict_config(request_config_dict, saved_config)
        elif isinstance(saved_config, list):
            request_config, is_update = self._process_list_config(request_config, saved_config)

        return request_config, is_update

    def _process_dict_config(self, request_config_dict: dict, saved_config: dict) -> (dict, bool):  # type: ignore
        is_update = False
        for key, value in request_config_dict.items():
            if request_config_dict[key] == len(saved_config[key]) * "*":
                request_config_dict[key] = saved_config[key]
            else:
                request_config_dict[key] = value
                is_update = True
        return request_config_dict, is_update

    def _process_list_config(self, request_config: list, saved_config: list) -> (list, bool):  # type: ignore
        is_update = False
        saved_config_dict = {config["key"]: config["value"] for config in saved_config}
        for config in request_config:
            if config["type"] == "secure" and saved_config_dict.get(config["key"]):
                if config["value"] == len(saved_config_dict[config["key"]]) * "*":
                    config["value"] = saved_config_dict[config["key"]]
                else:
                    is_update = True
        return request_config, is_update

    def push_to_minio(self, plugin_id: str, file_name: str):
        try:
            plugin_data = self.plugin_db_conn.fetch_plugin(plugin_id=plugin_id)
            file_path = os.path.join(PathConf.TEMP_PATH, file_name)

            _, file_extension = os.path.splitext(file_name)
            if file_extension.lower() not in [".zip", ".tar"]:
                content_type = "application/zip" if file_extension.lower() == ".zip" else "application/x-tar"
            else:
                raise ContentTypeError(f"Invalid file extension: {file_extension}")

            with open(file_path, "rb") as f:
                MinioUtility(
                    endpoint=MinioSettings.MINIO_ENDPOINT,
                    access_key=MinioSettings.MINIO_ACCESS_KEY,
                    secret_key=MinioSettings.MINIO_SECRET_KEY,
                    secure=MinioSettings.MINIO_SECURE,
                ).put_object(
                    MinioSettings.MINIO_BUCKET_NAME,
                    f"uploads/{plugin_id}/zip/{file_name}",
                    data=f,
                    length=os.path.getsize(file_path),
                    content_type=content_type,
                )
            os.remove(file_path)
            plugin_data.minio_file_path = f"uploads/{plugin_id}/zip/{file_name}"
            self.plugin_db_conn.update_plugin(plugin_id=plugin_id, data=plugin_data.model_dump())
            return (
                f"{MinioSettings.MINIO_ENDPOINT}/{MinioSettings.MINIO_BUCKET_NAME}/uploads/{plugin_id}/zip/{file_name}"
            )
        except Exception as e:
            logging.exception(f"Error occurred while uploading file to minio: {e}")

    @staticmethod
    def save_chunk(file_name: str, chunk: bytes):
        file_path = os.path.join(PathConf.TEMP_PATH, file_name)
        with open(file_path, "ab") as f:
            f.write(chunk)

    async def upload_files_to_minio_v2(self, plugin_id: str, file: UploadFile, background_tasks: BackgroundTasks):
        plugin_data = self.plugin_db_conn.fetch_plugin(plugin_id=plugin_id)
        if not plugin_data:
            raise PluginNotFoundError(f"Plugin ID {plugin_id} not found")
        elif plugin_data.plugin_type not in job_types:
            raise ValueError(f"Plugin type {plugin_data.plugin_type} not supported")
        file_name = file.filename
        content = await file.read()
        background_tasks.add_task(self.save_chunk, file_name, content)

    def upload_files_to_minio(self, plugin_id: str, file: UploadFile, version: float, user_details: MetaInfoSchema):
        plugin_data = self.plugin_db_conn.fetch_plugin(plugin_id=plugin_id, version=version)
        if not plugin_data:
            raise PluginNotFoundError(f"Plugin ID {plugin_id} not found")
        elif plugin_data.plugin_type not in job_types:
            raise ValueError(f"Plugin type {plugin_data.plugin_type} not supported")
        minio_util = MinioUtility(
            endpoint=MinioSettings.MINIO_ENDPOINT,
            access_key=MinioSettings.MINIO_ACCESS_KEY,
            secret_key=MinioSettings.MINIO_SECRET_KEY,
            secure=MinioSettings.MINIO_SECURE,
        )
        logging.info(f"Uploading file to minio for plugin ID: {plugin_id}")
        minio_util.upload_object(
            MinioSettings.MINIO_BUCKET_NAME,
            f"uploads/{plugin_id}/zip/{file.filename}",
            file.file,
        )
        plugin_data.minio_file_path = f"uploads/{plugin_id}/zip/{file.filename}"
        self.plugin_db_conn.update_plugin(
            plugin_id=plugin_id, data=plugin_data.model_dump(), version=plugin_data.version
        )
        notification = NotificationSchema(
            message=f"{plugin_data.name} uploaded Succesfully",
            plugin_type=plugin_data.plugin_type,
        )
        push_notification(notification, user_id=user_details.user_id, project_id=self.project_id)
        logging.info(f"Notification: {notification.model_dump()}")
        return (
            f"{MinioSettings.MINIO_ENDPOINT}/{MinioSettings.MINIO_BUCKET_NAME}/uploads/{plugin_id}/zip/{file.filename}"
        )

    @staticmethod
    def send_notification(plugin_data, plugin_id, user_details: MetaInfoSchema):
        """
        Send a notification after the Docker image has been saved locally.
        """
        notification = NotificationSchemaDownload(
            type="plugin",
            message=f"{plugin_data.name} is Ready to Download",
            notification_message=f"{plugin_data.name} is Ready Please download from the Notification Pane.",
            notification_status="success",
            report_type=plugin_data.plugin_type,
            download_link=plugin_id,
            download_url=f"/plugin-manager/api/v1/plugins{APIEndPoints.download_file}?plugin_id={plugin_id}&version={plugin_data.version}",
            mark_as_read=False,
        )
        push_notification_docker_download(
            notification, user_id=user_details.user_id, project_id=user_details.project_id
        )
        logging.info(
            f"Notification sent for Docker image {plugin_data.name} with download link {notification.download_url}"
        )
        return DefaultResponse(message=f"{plugin_data.name} is Ready Please download from the Notification Pane.")

    def docker_image_download(self, plugin_data, plugin_id, user_details: MetaInfoSchema):
        # Fetch the image tag from the database
        image_tag = next(
            (field["value"] for field in plugin_data.additional_fields if field["label"] == "Docker Image"), None
        )
        if not image_tag:
            raise ValueError("Docker Image tag not found in the plugin's additional fields")
        docker_util = DockerUtil()
        local_image_dir = PathConf.LOCAL_IMAGE_PATH / f"{plugin_data.name}"
        local_image_path = local_image_dir / "plugin.tar"

        # Ensure the local directory exists
        os.makedirs(local_image_dir, exist_ok=True)

        # Check if the image t"{"ar file exists locally if yes then remove it
        if os.path.exists(f"{local_image_dir}.zip"):
            os.remove(f"{local_image_dir}.zip")
            logging.info(f"Removed existing zip file: {local_image_path}")
        logging.info(f"Image {image_tag} is being pulled from registry")
        try:
            # Pull the image from the registry
            docker_util.pull_image(
                image_tag=image_tag,
                container_registry_url=AzureCredentials.azure_container_registry_url,
                container_registry_credentials={
                    "username": AzureCredentials.azure_registry_username,
                    "password": AzureCredentials.azure_registry_password,
                },
            )
            logging.info("Converting image to tar file and saving locally")
            # Save the image to the local path
            byte_stream = docker_util.save_image(image_tag)
            with open(local_image_path, "wb") as f:
                for chunk in byte_stream:
                    f.write(chunk)
            logging.info(f"Image {image_tag} saved locally as tar file: {local_image_path}")
            if plugin_data.plugin_type == "widget":
                shutil.copyfile(PathConf.LOCAL_IMAGE_PATH / f"{plugin_id}.json", local_image_dir / "widgetConfig.json")
            if plugin_data.plugin_type in ["custom_app", "formio_component"]:
                shutil.copyfile(PathConf.LOCAL_IMAGE_PATH / f"{plugin_id}.json", local_image_dir / "pluginConfig.json")
            self.docker_util.container_blob_signing(local_image_path, local_image_dir)
            source_dir = Path(local_image_dir)
            destination_zip = Path(f"{local_image_dir}.zip")
            shutil.make_archive(
                str(destination_zip.with_suffix("")),
                "zip",
                str(source_dir.parent),
                source_dir.name,
            )
            logging.info(f"Image and signature zipped as: {destination_zip}")
            shutil.rmtree(local_image_dir)
            # Send notification after saving the file
            PluginHandler.send_notification(plugin_data, plugin_id, user_details)

        except NotFound as e:
            logging.error(f"Image {image_tag} not found in registry: {e}")
            raise HTTPException(
                status_code=404,
                detail=f"Docker image {image_tag} not found in registry",
            ) from e
        except Exception as e:
            logging.error(f"Failed to create the tar file: {e}")
            raise HTTPException(status_code=500, detail="Failed to create the tar file")

    def docker_image_download_kubeflow(self, plugin_data, plugin_id, user_details: MetaInfoSchema):
        """
        Checks if the plugin_id is available and registration_type is kubeflow,
        then checks if the zip file is present in LOCAL_IMAGE_PATH. If yes, sends a notification.

        :param plugin_data: The plugin data.
        :param plugin_id: The plugin ID.
        :param user_details: The user details.
        """
        try:
            if plugin_data.plugin_type == "kubeflow":
                zip_file_path = PathConf.LOCAL_IMAGE_PATH / f"{plugin_data.name}.zip"
                if zip_file_path.exists():
                    self.send_notification(plugin_data, plugin_id, user_details)
                else:
                    logging.info(f"Zip file for Kubeflow plugin {plugin_id} is not available.")
            else:
                logging.info(f"Plugin {plugin_id} is not of type kubeflow.")
        except Exception as e:
            logging.error(f"Error checking plugin data or sending notification: {e}")

    def fetch_versions(self, plugin_id: str):
        data = self.plugin_db_conn.fetch_plugin_versions(plugin_id)
        sorted_versions = sorted(data, key=lambda x: float(x))
        formatted_data = [{"label": version, "value": version} for version in sorted_versions]
        return formatted_data

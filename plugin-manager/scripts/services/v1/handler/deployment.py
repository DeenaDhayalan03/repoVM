import datetime
import json
import logging
import os
import shutil
import time
import zipfile
from importlib import import_module
from pathlib import Path
from zoneinfo import ZoneInfo

import docker
import docker.errors
import kfp
import yaml
from docker.errors import APIError
from fastapi import BackgroundTasks, HTTPException
from ut_security_util import MetaInfoSchema
import copy

from scripts.config import (
    AzureCredentials,
    ExternalServices,
    MinioSettings,
    PathConf,
    Services,
    SonarQubeConfig,
    VulnerabilityScanner,
    KubeflowPortal,
)
from scripts.constants import (
    antivirus_scan_failed,
    job_types,
    kubeflow_url_not_found,
    redeployment_supported_types,
)
from scripts.constants.api import ExternalAPI
from scripts.core.engines.plugin_deployment_engines import DeploymentEngineMixin
from scripts.db import PluginMeta, VulnerablityScanReport
from scripts.db.mongo.ilens_configurations.collections.git_target import GitTarget
from scripts.db.mongo.ilens_widget.widget_plugin import WidgetPlugins
from scripts.db.schemas import PluginMetaDBSchema
from scripts.errors import (
    AlreadyDeployedError,
    AntiVirusScanFailed,
    CRONExpressionError,
    KubeflowPipelineConfigNotFound,
    ManifestError,
    PluginNotFoundError,
    SonarqubeScanFailed,
    VerficiationError,
)
from scripts.services.v1.schemas import DefaultResourceConfig
from scripts.services.v1.schemas import DeployPlugin as DeployPluginInputData
from scripts.utils.common_util import hit_external_service
from scripts.utils.docker_util import DockerUtil
from scripts.utils.external_services import deploy_plugin_request
from scripts.utils.git_tools import pull_code_from_git
from scripts.utils.minio_util import MinioUtility
from scripts.utils.notification_util import NotificationSchema, push_notification
from scripts.utils.sonarqube_scan import SonarQubeScan
from scripts.utils.common_util import extract_packages_and_image_from_yaml

PIPELINE_YML_FILENAME = "pipeline.yml"
DEPLOYMENT_STARTED = "Deployment Started"
DEPLOYMENT_FAILED = "Deployment Failed"
SCANNING_PROGRESS = "Scanning in progress"


class DeploymentHandler:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.plugin_db_conn = PluginMeta(project_id=project_id)
        self.widget_db_conn = WidgetPlugins(project_id=project_id)
        self.docker = DockerUtil()
        self.git_target_conn = GitTarget(project_id=project_id)

    def deploy_plugin(
        self,
        plugin_data: DeployPluginInputData,
        user_details: MetaInfoSchema,
        bg_task: BackgroundTasks,
    ):
        db_data = self.plugin_db_conn.fetch_plugin(plugin_id=plugin_data.plugin_id, version=plugin_data.version)

        if not db_data:
            msg = f"Plugin {plugin_data.plugin_id} not found"
            logging.exception(msg)
            raise PluginNotFoundError(msg)

        logging.debug("fetched plugin data")

        if db_data.plugin_type not in redeployment_supported_types:
            msg = f"Plugin {db_data.name} is already deployed"
            logging.exception(msg)
            raise AlreadyDeployedError(msg)
        logging.debug("Redeploying Resources")

        db_data.deployed_by = plugin_data.deployed_by
        db_data.deployed_on = datetime.datetime.now().replace(tzinfo=ZoneInfo("UTC"))
        db_data.portal = plugin_data.portal

        bg_task.add_task(
            self.deploy_and_register,
            plugin_data=db_data,
            user_details=user_details,
        )
        if db_data.plugin_type in job_types and db_data.plugin_type != "kubeflow" and not plugin_data.portal:
            bg_task.add_task(
                self.update_deployment_status,
                plugin_id=db_data.plugin_id,
                version=db_data.version,
                user_details=user_details,
            )

    def deploy_and_register(self, plugin_data: PluginMetaDBSchema, user_details: MetaInfoSchema):
        notification = NotificationSchema(
            message=f"Plugin: {plugin_data.name} has been registered successfully",
            plugin_type=plugin_data.plugin_type,
        )
        if plugin_data.plugin_type == "kubeflow" and plugin_data.portal:
            self.delete_kubeflow_local(plugin_data)
        try:
            plugin_data.deployment_status = "pending"
            base_plugin_store_func_map = {
                "project_upload": self.create_project_upload_plugin,
                "git": self.create_git_plugin,
                "bundle_upload": self.create_bundle_upload_plugin,
                "plugin_artifact": self.create_plugin_artifact_upload_plugin,
            }
            base_plugin_store_func = base_plugin_store_func_map.get(plugin_data.registration_type)
            plugin_data: PluginMetaDBSchema = base_plugin_store_func(plugin_data=plugin_data, user_details=user_details)
            # Refresh error logs
            plugin_data.errors = []
            if not plugin_data.portal:
                deployment_module = import_module(
                    f"scripts.core.engines.plugin_deployment_engines.{plugin_data.plugin_type.lower()}"
                )
                deployment_obj: DeploymentEngineMixin = deployment_module.DeploymentEngine(project_id=self.project_id)
                deployment_obj.register(plugin_data=plugin_data, user_details=user_details)
            if plugin_data.plugin_type == "widget" and plugin_data.portal:
                self.fetch_meta_for_portal_widget(plugin_data.plugin_id)
            if plugin_data.plugin_type in ["custom_app", "formio_component"] and plugin_data.portal:
                self.fetch_meta_for_portal_customapp(plugin_data.plugin_id)
            if plugin_data.plugin_type in job_types and plugin_data.plugin_type != "kubeflow":
                plugin_data.deployment_status = "deploying"
            else:
                plugin_data.deployment_status = "running"
        except Exception as e:
            plugin_data.errors = [str(e)]
        finally:
            if plugin_data.errors:
                logging.exception("Error occurred during deployment")
                notification.message = (
                    f"Error occurred while registering plugin: {plugin_data.name}\n"
                    f"Check details in Developer Plugins page."
                )
                notification.status = "error"
                plugin_data.deployment_status = "failed"
            if any([plugin_data.plugin_type not in job_types, plugin_data.errors]):
                push_notification(user_id=user_details.user_id, notification=notification, project_id=self.project_id)
            self.plugin_db_conn.update_plugin(
                plugin_id=plugin_data.plugin_id, data=plugin_data.model_dump(), version=plugin_data.version
            )

    def delete_kubeflow_local(self, plugin_data: PluginMetaDBSchema):
        local_image_dir = PathConf.LOCAL_IMAGE_PATH
        zip_file_path = Path(local_image_dir) / f"{plugin_data.name}.zip"

        # Check if the zip file exists and corresponds to the specific plugin
        if zip_file_path.exists():
            zip_file_path.unlink()
            logging.info(f"Deleted zip file: {zip_file_path}")
        else:
            logging.info(f"No zip file found for plugin {plugin_data.name} at: {zip_file_path}")

    @staticmethod
    def fetch_meta_for_portal_widget(plugin_id) -> dict:
        try:
            with open(PathConf.TEMP_PATH / f"{plugin_id}.json") as f:
                widget_config = json.loads(f.read())
            shutil.copyfile(PathConf.TEMP_PATH / f"{plugin_id}.json", PathConf.LOCAL_IMAGE_PATH / f"{plugin_id}.json")
            widget_config["files"] = None
            return widget_config or {}
        except Exception as e:
            logging.exception(f"Unable to fetch widget config during registration, {e}")
            return {}

    @staticmethod
    def fetch_meta_for_portal_customapp(plugin_id) -> dict:
        try:
            with open(PathConf.TEMP_PATH / f"{plugin_id}.json") as f:
                customapp_config = json.loads(f.read())
            shutil.copyfile(PathConf.TEMP_PATH / f"{plugin_id}.json", PathConf.LOCAL_IMAGE_PATH / f"{plugin_id}.json")
            customapp_config["files"] = None
            return customapp_config or {}
        except Exception as e:
            logging.exception(f"Unable to fetch custom app config during registration, {e}")
            return {}

    @staticmethod
    def create_project_upload_plugin(
        plugin_data: PluginMetaDBSchema, user_details: MetaInfoSchema
    ) -> PluginMetaDBSchema:
        try:
            logging.debug(user_details.model_dump())
            return plugin_data
        except Exception as e:
            logging.exception(e)
            plugin_data.errors.append(str(e))
            return plugin_data

    def create_git_plugin(self, plugin_data: PluginMetaDBSchema, user_details: MetaInfoSchema) -> PluginMetaDBSchema:
        folder_path = None
        try:
            # call function to pull code from git
            # add git build code here
            logging.info("In Create git plugin")

            # Note to dev: Never make this absolute path. Consider revising the rmdir on clone if dir exists
            git_target_details = self.git_target_conn.find_git_target(plugin_data.git_target_id)
            pull_root = Path(PathConf.CODE_STORE_PATH / "pull_path")
            pull_root.mkdir(parents=True, exist_ok=True)
            folder_path = Path(pull_root, plugin_data.name, plugin_data.plugin_id)
            logging.info(f"Cloning to {folder_path}")
            git_url = (
                git_target_details.get("git_common_url") + plugin_data.git_repository
                if plugin_data.git_target_id
                else plugin_data.git_url
            )
            git_username = (
                git_target_details.get("git_username") if plugin_data.git_target_id else plugin_data.git_username
            )
            git_access_token = (
                git_target_details.get("git_access_token")
                if plugin_data.git_target_id
                else plugin_data.git_access_token
            )
            pull_code_from_git(
                git_url=git_url,
                git_branch=plugin_data.git_branch,
                pull_path=folder_path,
                git_username=git_username,
                git_access_token=git_access_token,
            )
            logging.info(f"Plugin Type-->{plugin_data.plugin_type}")
            self._handle_plugin_type_git(plugin_data, user_details, folder_path)
            if plugin_data.deploy_as_container:
                return self.deploy_as_container(folder_path, plugin_data, user_details)
            return plugin_data
        except AlreadyDeployedError:
            self._cleanup_folder(folder_path)
            raise
        except (
            docker.errors.BuildError,
            docker.errors.APIError,
            FileNotFoundError,
            AntiVirusScanFailed,
            SonarqubeScanFailed,
        ):
            self._notify_deployment_failure(user_details, plugin_data)
            raise
        except Exception as e:
            logging.exception(f"Unexpected: {e}")
            raise

    def _handle_plugin_type_git(self, plugin_data, user_details, folder_path):
        if plugin_data.plugin_type in job_types and plugin_data.plugin_type != "kubeflow":
            self._handle_job_type_plugin_git(plugin_data, folder_path)
        elif plugin_data.plugin_type == "kubeflow":
            self._handle_kubeflow_plugin_git(plugin_data, user_details, folder_path)

    def _handle_job_type_plugin_git(self, plugin_data, folder_path):
        if plugin_data.plugin_type == "widget":
            self.find_widget_configuration(plugin_data.name, plugin_data.plugin_id, folder_path)
        elif plugin_data.plugin_type in ["custom_app", "formio_component"]:
            self.find_plugin_configuration(plugin_data.name, plugin_data.plugin_id, folder_path)
        plugin_data.deployment_status = "scanning"
        self.plugin_db_conn.update_plugin(plugin_data.plugin_id, plugin_data.model_dump(), version=plugin_data.version)
        self.antivirus_scan(plugin_data)
        self.sonarqube_scan(plugin_data)

    def _handle_kubeflow_plugin_git(self, plugin_data, user_details, folder_path):
        self.plugin_db_conn.update_plugin(
            plugin_data.plugin_id, {"status": DEPLOYMENT_STARTED}, version=plugin_data.version
        )
        if not plugin_data.portal and self.configure_kubeflow_pipeline(plugin_data, user_details, folder_path):
            plugin_data.deployment_status = "running"
        elif plugin_data.portal:
            extract_packages_and_image_from_yaml(
                yaml_file_path=folder_path / PIPELINE_YML_FILENAME,
                output_file_path=folder_path / "kubeflow_requirements.txt",
                name=plugin_data.name,
            )
            self.plugin_db_conn.update_plugin(
                plugin_data.plugin_id, {"status": SCANNING_PROGRESS, "version": plugin_data.version}
            )

    def _cleanup_folder(self, folder_path):
        if folder_path and folder_path.exists():
            logging.warning(f"****DELETING CLONED REPO AS VERSION ALREADY DEPLOYED {folder_path}")
            shutil.rmtree(folder_path)

    def _notify_deployment_failure(self, user_details, plugin_data):
        push_notification(
            user_id=user_details.user_id,
            notification=NotificationSchema(
                message=f"Plugin: {plugin_data.name} deployment failed",
                plugin_type=plugin_data.plugin_type,
            ),
            project_id=self.project_id,
        )

    def create_plugin_artifact_upload_plugin(
        self, plugin_data: PluginMetaDBSchema, user_details: MetaInfoSchema
    ) -> PluginMetaDBSchema:
        try:
            file_name = plugin_data.minio_file_path.split("/")[-1]
            download_path = Path(PathConf.CODE_STORE_PATH / "pull_path")
            download_path.mkdir(parents=True, exist_ok=True)
            download_path = download_path / f"{plugin_data.name}/{plugin_data.plugin_id}/"
            MinioUtility(
                endpoint=MinioSettings.MINIO_ENDPOINT,
                access_key=MinioSettings.MINIO_ACCESS_KEY,
                secret_key=MinioSettings.MINIO_SECRET_KEY,
                secure=MinioSettings.MINIO_SECURE,
            ).download_object(
                bucket_name=MinioSettings.MINIO_BUCKET_NAME,
                object_name=plugin_data.minio_file_path,
                file_path=str(f"{download_path}/{file_name}"),
            )
            zip_file_name = file_name.split(".")[0]
            with zipfile.ZipFile(f"{str(download_path)}/{file_name}", "r") as zip_ref:
                zip_ref.extractall(path=f"{str(download_path)}")
            if plugin_data.plugin_type == "kubeflow":
                self._handle_kubeflow_plugin(
                    plugin_data, user_details=user_details, folder_path=f"{str(download_path)}/{zip_file_name}"
                )
                return plugin_data
            if not self.docker.container_blob_verifying(f"{str(download_path)}/{zip_file_name}"):
                self.plugin_db_conn.update_plugin(
                    plugin_data.plugin_id, {"status": "Verification Failed"}, version=plugin_data.version
                )
                raise VerficiationError("Blob verification failed")
            self.plugin_db_conn.update_plugin(
                plugin_data.plugin_id, {"status": "Verification Success"}, version=plugin_data.version
            )
            new_image_name = f"{plugin_data.name}-{plugin_data.plugin_type}:{plugin_data.version}".lower().replace(
                " ", "_"
            )
            self.docker.load_docker_image(
                docker_tar_file_path=f"{download_path}/{zip_file_name}/plugin.tar",
                new_image_name=new_image_name,
                container_registry_url=AzureCredentials.azure_container_registry_url,
                container_registry_credentials={
                    "username": AzureCredentials.azure_registry_username,
                    "password": AzureCredentials.azure_registry_password,
                },
            )
            if plugin_data.plugin_type == "widget":
                self.find_widget_configuration(
                    plugin_data.name, plugin_data.plugin_id, f"{download_path}/{zip_file_name}/widgetConfig.json", True
                )
            elif plugin_data.plugin_type in ["custom_app", "formio_component"]:
                self.find_plugin_configuration(
                    plugin_data.name, plugin_data.plugin_id, f"{download_path}/{zip_file_name}/pluginConfig.json", True
                )
            shutil.rmtree(download_path)
            if plugin_data.deploy_as_container:
                return self.deploy_as_container("", plugin_data, user_details)
            return plugin_data
        except Exception as e:
            logging.exception(f"Unexpected: {e}")
            shutil.rmtree(f"{download_path}/{file_name}")
            shutil.rmtree(f"{download_path}/{zip_file_name}")

    def create_bundle_upload_plugin(
        self, plugin_data: PluginMetaDBSchema, user_details: MetaInfoSchema
    ) -> PluginMetaDBSchema:
        try:
            file_name = plugin_data.minio_file_path.split("/")[-1]
            download_path = self._prepare_download_path(plugin_data)
            self._download_and_extract_file(plugin_data, file_name, download_path)
            folder_path = f"{str(download_path)}/{file_name}".replace(".zip", "")
            logging.info(f"Plugin Type-->{plugin_data.plugin_type}")
            self._handle_plugin_type(plugin_data, user_details, folder_path)
            if plugin_data.deploy_as_container:
                return self.deploy_as_container(Path(folder_path), plugin_data, user_details)
            return plugin_data
        except Exception as e:
            logging.exception(f"Unexpected: {e}")
            raise

    def _prepare_download_path(self, plugin_data):
        download_path = Path(PathConf.CODE_STORE_PATH / "pull_path")
        download_path.mkdir(parents=True, exist_ok=True)
        return download_path / f"{plugin_data.name}/{plugin_data.plugin_id}/"

    def _download_and_extract_file(self, plugin_data, file_name, download_path):
        MinioUtility(
            endpoint=MinioSettings.MINIO_ENDPOINT,
            access_key=MinioSettings.MINIO_ACCESS_KEY,
            secret_key=MinioSettings.MINIO_SECRET_KEY,
            secure=MinioSettings.MINIO_SECURE,
        ).download_object(
            bucket_name=MinioSettings.MINIO_BUCKET_NAME,
            object_name=plugin_data.minio_file_path,
            file_path=str(f"{download_path}/{file_name}"),
        )
        with zipfile.ZipFile(f"{str(download_path)}/{file_name}", "r") as zip_ref:
            zip_ref.extractall(path=f"{str(download_path)}")
        os.remove(f"{str(download_path)}/{file_name}")

    def _handle_plugin_type(self, plugin_data, user_details, folder_path):
        if plugin_data.plugin_type in job_types and plugin_data.plugin_type != "kubeflow":
            self._handle_job_type_plugin(plugin_data, folder_path)
        if plugin_data.plugin_type == "kubeflow" and Path(f"{folder_path}/kubeflow.tar").exists():
            logging.error("Please upload as Plugin Artifact")
            raise ValueError("Please upload as Plugin Artifact")
        elif plugin_data.plugin_type == "kubeflow":
            self._handle_kubeflow_plugin(plugin_data, user_details, folder_path)

    def _handle_job_type_plugin(self, plugin_data, folder_path):
        plugin_data.deployment_status = "scanning"
        self.plugin_db_conn.update_plugin(plugin_data.plugin_id, plugin_data.model_dump(), version=plugin_data.version)
        if plugin_data.plugin_type == "widget":
            logging.info(f"Finding widget configuration {folder_path}")
            self.find_widget_configuration(plugin_data.name, plugin_data.plugin_id, folder_path)
        elif plugin_data.plugin_type in ["custom_app", "formio_component"]:
            self.find_plugin_configuration(plugin_data.name, plugin_data.plugin_id, folder_path)
        self.antivirus_scan(plugin_data)
        self.sonarqube_scan(plugin_data)

    def _handle_kubeflow_plugin(self, plugin_data, user_details, folder_path):
        self.plugin_db_conn.update_plugin(
            plugin_data.plugin_id, {"status": DEPLOYMENT_STARTED}, version=plugin_data.version
        )
        if not getattr(plugin_data, "portal", False):
            if plugin_data.registration_type == "plugin_artifact":
                if not Path(f"{folder_path}/kubeflow.tar").exists():
                    self.plugin_db_conn.update_plugin(
                        plugin_data.plugin_id, {"status": DEPLOYMENT_FAILED}, version=plugin_data.version
                    )
                    raise HTTPException(status_code=400, detail="Missing required file: kubeflow.tar")
            if Path(f"{folder_path}/kubeflow.tar").exists():
                self.configure_offline_kubeflow_pipeline(plugin_data, folder_path, user_details)
            if self.configure_kubeflow_pipeline(plugin_data, user_details, folder_path):
                plugin_data.deployment_status = "running"

        else:
            folder_path = Path(folder_path)
            extract_packages_and_image_from_yaml(
                yaml_file_path=folder_path / PIPELINE_YML_FILENAME,
                output_file_path=folder_path / "kubeflow_requirements.txt",
                name=plugin_data.name,
            )
            self.plugin_db_conn.update_plugin(
                plugin_data.plugin_id, {"status": SCANNING_PROGRESS}, version=plugin_data.version
            )

    def update_yaml_with_secret(self, yaml_file_path, image_pull_secret):
        try:
            with open(yaml_file_path) as file:
                yaml_documents = list(yaml.safe_load_all(file))
            platforms_section_exists = any("platforms" in doc for doc in yaml_documents)
            if platforms_section_exists:
                self._update_existing_platforms(yaml_documents, image_pull_secret)
            else:
                self._add_platforms_section(yaml_documents, image_pull_secret)
            with open(yaml_file_path, "w") as file:
                yaml.dump_all(yaml_documents, file)
        except Exception as e:
            print(f"Error updating the YAML file: {e}")

    def _update_existing_platforms(self, yaml_documents, image_pull_secret):
        for doc in yaml_documents:
            executors = doc.get("platforms", {}).get("kubernetes", {}).get("deploymentSpec", {}).get("executors", {})
            for _executor, details in executors.items():
                details["imagePullSecret"] = [{"secretName": image_pull_secret}]
        print(f"YAML file updated with imagePullSecret: '{image_pull_secret}' in each executor.")

    def _add_platforms_section(self, yaml_documents, image_pull_secret):
        platforms_section = {"platforms": {"kubernetes": {"deploymentSpec": {"executors": {}}}}}
        for doc in yaml_documents:
            if isinstance(doc, dict):
                components = doc.get("components", {})
                for _key, value in components.items():
                    if isinstance(value, dict) and "executorLabel" in value:
                        executor_label = value["executorLabel"]
                        platforms_section["platforms"]["kubernetes"]["deploymentSpec"]["executors"][executor_label] = {
                            "imagePullSecret": [{"secretName": image_pull_secret}]
                        }
        yaml_documents.append(platforms_section)
        print("YAML file updated with platforms section for executors based on 'executorLabel' keys.")

    def configure_offline_kubeflow_pipeline(
        self, plugin_data: PluginMetaDBSchema, folder_path, user_details: MetaInfoSchema
    ):
        self.plugin_db_conn.update_plugin(
            plugin_data.plugin_id, {"status": DEPLOYMENT_STARTED}, version=plugin_data.version
        )
        try:
            if not self.docker.container_blob_verifying(f"{folder_path}", kubeflow=True):
                self.plugin_db_conn.update_plugin(
                    plugin_data.plugin_id, {"status": "Verification Failed"}, version=plugin_data.version
                )
                raise VerficiationError("Blob verification failed")

            new_image_name = self.get_new_image_name(plugin_data)
            if Path(f"{folder_path}/kubeflow.tar").exists():
                image_full_tag = self.load_and_push_image(folder_path, new_image_name)
                self.update_pipeline_document(folder_path, image_full_tag)
                self.update_yaml_with_secret(f"{folder_path}/pipeline.yml", KubeflowPortal.IMAGE_PULL_SECRET)
            push_notification(
                user_id=user_details.user_id,
                notification=NotificationSchema(
                    message=f"Plugin: {plugin_data.name} has been Scanned succesfully",
                    plugin_type=plugin_data.plugin_type,
                    plugin_id=plugin_data.plugin_id,
                ),
                project_id=self.project_id,
            )

        except Exception as e:
            self.plugin_db_conn.update_plugin(
                plugin_data.plugin_id, {"status": DEPLOYMENT_FAILED}, version=plugin_data.version
            )
            logging.exception(f"Error occurred while configuring Kubeflow pipeline {e}")
            raise e

    def get_new_image_name(self, plugin_data):
        return f"{plugin_data.name}-{plugin_data.plugin_type}:{plugin_data.version}".lower().replace(" ", "_")

    def load_and_push_image(self, folder_path, new_image_name):
        self.docker.load_docker_image(
            docker_tar_file_path=f"{folder_path}/kubeflow.tar",
            new_image_name=new_image_name,
            container_registry_url=AzureCredentials.azure_container_registry_url,
            container_registry_credentials={
                "username": AzureCredentials.azure_registry_username,
                "password": AzureCredentials.azure_registry_password,
            },
        )
        image_full_tag = self.docker.push_docker_image(
            image_tag=new_image_name,
            container_registry_url=AzureCredentials.azure_container_registry_url,
            container_registry_credentials={
                "username": AzureCredentials.azure_registry_username,
                "password": AzureCredentials.azure_registry_password,
            },
        )
        self.docker.container_signing(image_full_tag)
        return image_full_tag

    def update_pipeline_document(self, folder_path, image_full_tag):
        with open(f"{folder_path}/pipeline.yml") as f:
            pipeline_documents = list(yaml.safe_load_all(f))
        if len(pipeline_documents) > 0:
            pipeline = pipeline_documents[0]
            if "deploymentSpec" in pipeline and "executors" in pipeline["deploymentSpec"]:
                executors = pipeline["deploymentSpec"]["executors"]
                for executor in executors.values():
                    if "container" in executor and "image" in executor["container"]:
                        executor["container"]["image"] = image_full_tag
        else:
            logging.warning("The 'spec' or 'templates' key is missing in the pipeline document.")

        with open(f"{folder_path}/pipeline.yml", "w") as f:
            yaml.dump_all(pipeline_documents, f)

    def find_widget_configuration(self, plugin_name: str, plugin_id, folder_path, artifact=False):
        if not os.path.exists(PathConf.TEMP_PATH):
            os.makedirs(PathConf.TEMP_PATH, exist_ok=True)
        try:
            config_in_repo = folder_path if artifact else f"{folder_path}/frontend/src/assets/widgetConfig.json"
            if not os.path.exists(config_in_repo):
                raise FileNotFoundError("Widget configuration not found")
            docs_in_repo = f"{folder_path}/user_manual"
            if os.path.exists(docs_in_repo):
                with open(config_in_repo, "r+") as f:
                    data = json.load(f)
                    data["docs"] = f"gateway/plugin/{plugin_name.lower().replace('_', '-')}/api/widget/docs"
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f)
            shutil.copyfile(config_in_repo, PathConf.TEMP_PATH / f"{plugin_id}.json")
        except Exception as e:
            logging.exception(f"Unable to copy widget configuration to temp folder, {e}")
            raise

    @staticmethod
    def find_plugin_configuration(plugin_name: str, plugin_id, folder_path, artifact=False):
        if not os.path.exists(PathConf.TEMP_PATH):
            os.makedirs(PathConf.TEMP_PATH, exist_ok=True)
        try:
            config_in_repo = folder_path if artifact else f"{folder_path}/frontend/src/assets/pluginConfig.json"
            if not os.path.exists(config_in_repo):
                raise FileNotFoundError("Plugin configuration not found")
            docs_in_repo = f"{folder_path}/user_manual"
            if os.path.exists(docs_in_repo):
                with open(config_in_repo, "r+") as f:
                    data = json.load(f)
                    data["docs"] = f"gateway/plugin/{plugin_name.lower().replace('_', '-')}/api/plugin/docs"
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f)
            shutil.copyfile(config_in_repo, PathConf.TEMP_PATH / f"{plugin_id}.json")
        except Exception as e:
            logging.exception(f"Unable to copy plugin configuration to temp folder, {e}")
            raise

    def deploy_as_container(
        self,
        folder_path: Path,
        plugin_data: PluginMetaDBSchema,
        user_details: MetaInfoSchema,
    ):
        configurations = copy.deepcopy(plugin_data.configurations)
        try:
            self.validate_plugin_files(plugin_data, folder_path)
            image_full_tag = self.build_and_push_image(plugin_data, folder_path)
            config_list, port = self.prepare_configurations(configurations, plugin_data)
            self.perform_vulnerability_scan(plugin_data, image_full_tag)
            resources = self.allocate_resources(plugin_data)
            deploy_plugin_req = self.create_deploy_request(plugin_data, image_full_tag, config_list, port, resources)
            return self.deploy_plugin_code(deploy_plugin_req, plugin_data, user_details)
        except docker.errors.BuildError as build_error:
            self.handle_build_error(build_error, plugin_data)
        except docker.errors.APIError as api_error:
            logging.exception(f"Docker API Error:{api_error}")
            raise
        except Exception as e:
            logging.exception(f"An error occurred:{e}")
            plugin_data.errors.append(str(e))
            return plugin_data

    def validate_plugin_files(self, plugin_data, folder_path):
        if (
            plugin_data.registration_type != "plugin_artifact"
            and plugin_data.plugin_type == "widget"
            and not os.path.exists(folder_path / "manifest.json")
        ):
            raise ManifestError("Manifest file not found widget")
        elif (
            plugin_data.registration_type != "plugin_artifact"
            and plugin_data.plugin_type == "microservice"
            and not os.path.exists(folder_path / "Dockerfile")
        ):
            raise APIError("Dockerfile not found for microservice")

    def build_and_push_image(self, plugin_data, folder_path):
        if plugin_data.registration_type == "plugin_artifact":
            return self.handle_plugin_artifact(plugin_data)
        elif os.path.exists(folder_path / "Dockerfile"):
            return self.build_from_dockerfile(plugin_data, folder_path)
        else:
            return self.build_from_manifest(plugin_data, folder_path)

    def handle_plugin_artifact(self, plugin_data):
        self.plugin_db_conn.update_plugin(
            plugin_data.plugin_id, {"status": DEPLOYMENT_STARTED}, version=plugin_data.version
        )
        plugin_data.deployment_status = "deploying"
        self.plugin_db_conn.update_plugin(plugin_data.plugin_id, plugin_data.model_dump(), version=plugin_data.version)
        image_tag = f"{plugin_data.name}-{plugin_data.plugin_type}:{plugin_data.version}".lower().replace(" ", "_")
        image_full_tag = self.docker.push_docker_image(
            image_tag=image_tag,
            container_registry_url=AzureCredentials.azure_container_registry_url,
            container_registry_credentials={
                "username": AzureCredentials.azure_registry_username,
                "password": AzureCredentials.azure_registry_password,
            },
        )
        self.docker.container_signing(image_full_tag)
        return image_full_tag

    def build_from_dockerfile(self, plugin_data, folder_path):
        logging.info("Building from Dockerfile")
        plugin_data.deployment_status = "deploying"
        self.plugin_db_conn.update_plugin(plugin_data.plugin_id, plugin_data.model_dump(), version=plugin_data.version)
        image_tag = f"{plugin_data.name}-{plugin_data.plugin_type}:{plugin_data.version}".lower().replace(" ", "_")
        self.docker.build_docker_image(
            str(folder_path),
            image_tag=image_tag,
            container_registry_url=AzureCredentials.azure_container_registry_url,
            build_args=Services.PLUGIN_BUILD_ARGS,
        )
        image_full_tag = self.docker.push_docker_image(
            image_tag=image_tag,
            container_registry_url=AzureCredentials.azure_container_registry_url,
            container_registry_credentials={
                "username": AzureCredentials.azure_registry_username,
                "password": AzureCredentials.azure_registry_password,
            },
        )
        self.docker.container_signing(image_full_tag)
        return image_full_tag

    def build_from_manifest(self, plugin_data, folder_path):
        logging.info("Building from manifest")
        self.plugin_db_conn.update_plugin(
            plugin_data.plugin_id, {"status": SCANNING_PROGRESS}, version=plugin_data.version
        )
        plugin_data.deployment_status = "deploying"
        self.plugin_db_conn.update_plugin(plugin_data.plugin_id, plugin_data.model_dump(), version=plugin_data.version)
        with open(folder_path / "manifest.json") as f:
            config = json.load(f)
        if os.path.exists(folder_path / "user_manual"):
            self.docker.dockerfile_generator(folder_path, config, docs=True)
        else:
            self.docker.dockerfile_generator(folder_path, config)
        image_tag = f"{config['plugin_name']}-{config['plugin_type']}:{plugin_data.version}".lower().replace(" ", "_")
        self.docker.build_docker_image(
            str(folder_path),
            image_tag=image_tag,
            container_registry_url=AzureCredentials.azure_container_registry_url,
            build_args=Services.PLUGIN_BUILD_ARGS,
        )
        self.plugin_db_conn.update_plugin(
            plugin_data.plugin_id, {"status": SCANNING_PROGRESS}, version=plugin_data.version
        )
        image_full_tag = self.docker.push_docker_image(
            image_tag=image_tag,
            container_registry_url=AzureCredentials.azure_container_registry_url,
            container_registry_credentials={
                "username": AzureCredentials.azure_registry_username,
                "password": AzureCredentials.azure_registry_password,
            },
        )
        self.docker.container_signing(image_full_tag)
        return image_full_tag

    def prepare_configurations(self, configurations, plugin_data):
        config_list = []
        port = str(plugin_data.container_port)
        if isinstance(configurations, dict):
            config_list = [
                {"key": env_var, "value": env_val, "type": "text"} for env_var, env_val in configurations.items()
            ]
            port = str(configurations.get("PORT", plugin_data.container_port))
        elif isinstance(configurations, list):
            config_list = configurations
            for config in config_list:
                if config.get("key") in ["PORT", "port"]:
                    port = str(config.get("value", plugin_data.container_port))
                    break
        if all(config.get("key") != "PORT" for config in config_list):
            config_list.append({"key": "PORT", "value": port, "type": "text"})
        return config_list, port

    def perform_vulnerability_scan(self, plugin_data, image_full_tag):
        if VulnerabilityScanner.VULNERABILITY_SCAN and self.docker.scan_image(
            image_full_tag,
            folder_path=f"/{plugin_data.name}-{plugin_data.plugin_id}",
            plugin_data=plugin_data,
        ):
            report = self.docker.scan_report_parser(folder_path=f"/{plugin_data.name}-{plugin_data.plugin_id}")
            if report.get("vulnerabilities"):
                vulnerability_report = VulnerablityScanReport(project_id=self.project_id)
                vulnerability_report.update_record(plugin_data.plugin_id, report)
                plugin_data.security_checks.vulnerabilities = False
                self.plugin_db_conn.update_plugin(
                    plugin_data.plugin_id,
                    {
                        "status": "Vulnerability Scan Failed",
                        "security_checks": plugin_data.security_checks.model_dump(),
                    },
                    version=plugin_data.version,
                )
            plugin_data.security_checks.vulnerabilities = True
            self.plugin_db_conn.update_plugin(
                plugin_data.plugin_id,
                {
                    "status": SCANNING_PROGRESS,
                    "security_checks": plugin_data.security_checks.model_dump(),
                },
                version=plugin_data.version,
            )
            if plugin_data.portal:
                self.plugin_db_conn.update_plugin(
                    plugin_data.plugin_id, {"status": "Scan Successful"}, version=plugin_data.version
                )
            if plugin_data.registration_type == "plugin_artifact":
                self.security_check_plugin_artifact(plugin_data)
        else:
            logging.info("Skipping vulnerability scan")
            plugin_data.security_checks.vulnerabilities = True
            self.plugin_db_conn.update_plugin(
                plugin_data.plugin_id,
                {
                    "status": SCANNING_PROGRESS,
                    "security_checks": plugin_data.security_checks.model_dump(),
                },
                version=plugin_data.version,
            )
            if plugin_data.portal:
                self.plugin_db_conn.update_plugin(
                    plugin_data.plugin_id, {"status": "Scan Successful"}, version=plugin_data.version
                )
            if plugin_data.registration_type == "plugin_artifact":
                self.security_check_plugin_artifact(plugin_data)

    def security_check_plugin_artifact(self, plugin_data: PluginMetaDBSchema):
        if plugin_data.registration_type == "plugin_artifact" and plugin_data.security_checks.vulnerabilities:
            plugin_data.security_checks.sonarqube = True
            plugin_data.security_checks.antivirus = True

        self.plugin_db_conn.update_plugin(
            plugin_data.plugin_id,
            {
                "security_checks": plugin_data.security_checks.model_dump(),
            },
            version=plugin_data.version,
        )

    def allocate_resources(self, plugin_data):
        if plugin_data.advancedConfiguration:
            resources = self.resource_allocation(plugin_data.advancedConfiguration.bodyContent)
        else:
            resources = DefaultResourceConfig().model_dump()
        return resources

    def create_deploy_request(self, plugin_data, image_full_tag, config_list, port, resources):
        return {
            "app_name": plugin_data.name,
            "image": image_full_tag,
            "app_id": plugin_data.plugin_id,
            "project_id": self.project_id,
            "app_version": str(plugin_data.version),
            "env_var": config_list,
            "port": int(port),
            "resources": resources,
        }

    def deploy_plugin_code(self, deploy_plugin_req, plugin_data, user_details):
        if plugin_data.portal:
            self.plugin_db_conn.update_plugin(
                plugin_data.plugin_id, plugin_data.model_dump(), version=plugin_data.version
            )
            self._update_docker_image_field(plugin_data, deploy_plugin_req["image"])
            return plugin_data
        logging.info(f"Deployment request {deploy_plugin_req}")
        resp = deploy_plugin_request(data=deploy_plugin_req, user_details=user_details)
        logging.info(f"Deployment response {resp}")
        proxy_path = resp.get("proxy-path")
        logging.info(f"Proxy path is {proxy_path}")
        plugin_data.proxy = proxy_path
        self.plugin_db_conn.update_plugin(plugin_data.plugin_id, plugin_data.model_dump(), version=plugin_data.version)
        self._update_docker_image_field(plugin_data, deploy_plugin_req["image"])
        return plugin_data

    def _update_docker_image_field(self, plugin_data, image_value):
        for field in plugin_data.additional_fields:
            if field.get("label") == "Docker Image":
                field["value"] = image_value
                break
        else:
            plugin_data.additional_fields.append({"label": "Docker Image", "value": image_value})

    def handle_build_error(self, build_error, plugin_data):
        build_logs = "".join(str(line[list(line.keys())[0]]) for line in build_error.build_log)
        plugin_data.errors.append(build_logs)
        logging.exception(f"Docker Build Error:{build_logs}")
        raise

    def update_deployment_status(self, plugin_id: str, version: float, user_details: MetaInfoSchema):
        def check_deployment_status(payload):
            resp = hit_external_service(
                api_url=f"{ExternalServices.PROXY_MANAGER_URL}{ExternalAPI.deployment_status}",
                payload=payload,
            )
            return resp

        plugin_data = self.plugin_db_conn.fetch_plugin(plugin_id=plugin_id, version=version)
        if plugin_data.deployment_status == "failed":
            logging.info("Deployment failed")
            logging.info(f"Deleting plugin {plugin_data.name}")
            self.plugin_db_conn.update_plugin(
                plugin_data.plugin_id, {"status": DEPLOYMENT_FAILED}, version=plugin_data.version
            )
            try:
                resp = hit_external_service(
                    api_url=f"{ExternalServices.PROXY_MANAGER_URL}{ExternalAPI.delete_resources}",
                    payload={
                        "app_name": plugin_data.name,
                        "app_id": plugin_data.plugin_id,
                    },
                )
                logging.info(f"Delete response {resp}")
                self.plugin_db_conn.update_plugin(plugin_id=plugin_id, data=plugin_data.model_dump(), version=version)
                return
            except Exception as e:
                logging.exception(f"Failed to delete plugin {e}")
                return

        payload = {"plugin_list": [f"{plugin_data.name}-{plugin_data.plugin_id}"]}
        plugin_obj = PluginMeta(self.project_id)
        time.sleep(5)
        resp = check_deployment_status(payload)
        while resp.get("data")[0].get("status") == "in_progress":
            time.sleep(5)
            resp = check_deployment_status(payload)

        if resp.get("data")[0].get("status") == "completed":
            logging.info("Deployment completed")
            plugin_obj.update_plugin(
                plugin_data.plugin_id,
                {"deployment_status": "running", "status": "running"},
                version=plugin_data.version,
            )
            push_notification(
                user_id=user_details.user_id,
                notification=NotificationSchema(
                    message=f"Plugin: {plugin_data.name} has been deployed successfully",
                    plugin_type=plugin_data.plugin_type,
                    plugin_id=plugin_data.plugin_id,
                ),
                project_id=self.project_id,
            )
            self.update_widget_plugin(plugin_data)
        elif resp.get("data")[0].get("status") == "error":
            for pods in resp.get("data")[0].get("pods"):
                for container in pods.get("containers"):
                    if container.get("status") == "error":
                        plugin_data.errors.append(f'{container.get("reason")} {container.get("message")}')

            logging.info("Deployment failed")
            plugin_obj.update_plugin(
                plugin_data.plugin_id, {"deployment_status": "failed"}, version=plugin_data.version
            )
            self.plugin_db_conn.update_plugin(
                plugin_data.plugin_id, {"status": DEPLOYMENT_FAILED}, version=plugin_data.version
            )
            push_notification(
                user_id=user_details.user_id,
                notification=NotificationSchema(
                    message=f"Plugin: {plugin_data.name} deployment failed",
                    plugin_type=plugin_data.plugin_type,
                ),
                project_id=self.project_id,
            )

    def update_widget_plugin(self, plugin_data: PluginMetaDBSchema):
        if self.widget_db_conn.fetch_widget_plugin(plugin_data.plugin_id):
            resp = hit_external_service(
                api_url=f"{Services.HOME_LINK}{plugin_data.proxy}widget/load_styles", method="get"
            )
            if resp.get("data") and resp.get("status") == "success":
                self.widget_db_conn.update_widget_plugin(
                    plugin_id=plugin_data.plugin_id,
                    data={"meta.files": resp.get("data")},
                )

    def start_stop_plugin(
        self,
        plugin_id: str,
        bg_task: BackgroundTasks,
    ):
        plugin_data = self.plugin_db_conn.fetch_plugin_for_start_stop(plugin_id=plugin_id)
        if not plugin_data:
            raise PluginNotFoundError(f"Plugin ID {plugin_id} not found")

        if plugin_data.deployment_status == "stopped":
            plugin_data.deployment_status = "running"
        else:
            plugin_data.deployment_status = "stopped"
        hit_external_service(
            api_url=f"{ExternalServices.PROXY_MANAGER_URL}{ExternalAPI.plugin_switch}",
            params={
                "plugin": f"{plugin_data.name.lower().replace('_', '-')}-{plugin_data.plugin_id.lower()}",
                "status": plugin_data.deployment_status,
            },
            method="get",
        )
        bg_task.add_task(
            self.update_plugin_status,
            plugin_name=plugin_data.name,
            plugin_id=plugin_id,
        )
        self.plugin_db_conn.update_plugin(
            plugin_id=plugin_id,
            data={"deployment_status": plugin_data.deployment_status},
            version=plugin_data.version,
        )
        return f"Plugin {plugin_data.name} {plugin_data.deployment_status}"

    def update_plugin_status(self, plugin_name: str, plugin_id: str):
        payload = {"plugin_list": [f"{plugin_name}-{plugin_id}"]}
        resp = hit_external_service(
            api_url=f"{ExternalServices.PROXY_MANAGER_URL}{ExternalAPI.deployment_status}",
            payload=payload,
        )
        if not resp.get("data"):
            return None
        while resp.get("data")[0].get("status") == "in_progress":
            time.sleep(3)
            resp = hit_external_service(
                api_url=f"{ExternalServices.PROXY_MANAGER_URL}{ExternalAPI.deployment_status}",
                payload=payload,
            )
        if resp.get("data")[0].get("status") == "completed":
            if resp.get("data")[0].get("replicas") > 0:
                logging.info("Plugin Started")
                return "running"
            elif resp.get("data")[0].get("replicas") == 0:
                logging.info("Plugin Stopped")
                return "stopped"

    @staticmethod
    def resource_allocation(bodycontent: list):  # NOSONAR
        resources = {}
        for data in bodycontent:
            if data.get("property") == "replicas":
                replicas = data.get("input")
                resources["replicas"] = replicas
            elif data.get("property") == "cpu_request":
                cpu_request = f'{str(data.get("input"))}'
                resources["cpu_request"] = cpu_request

            elif data.get("property") == "cpu_limit":
                cpu_limit = f'{str(data.get("input"))}'
                resources["cpu_limit"] = cpu_limit
            elif data.get("property") == "memory_request":
                memory_request = f'{int(data.get("input")*1024)}Mi'
                resources["memory_request"] = memory_request

            elif data.get("property") == "memory_limit":
                memory_limit = f'{int(data.get("input")*1024)}Mi'
                resources["memory_limit"] = memory_limit

        if resources.get("memory_request") and not resources.get("memory_limit"):
            resources["memory_limit"] = resources["memory_request"]
        if resources.get("cpu_request") and not resources.get("cpu_limit"):
            resources["cpu_limit"] = resources["cpu_request"]
        if resources.get("memory_limit") and not resources.get("memory_request"):
            resources["memory_request"] = "0"
        if resources.get("cpu_limit") and not resources.get("cpu_request"):
            resources["cpu_request"] = "0"
        return resources

    def antivirus_scan(self, plugin_data: PluginMetaDBSchema):
        self.plugin_db_conn.update_plugin(
            plugin_data.plugin_id, {"status": SCANNING_PROGRESS}, version=plugin_data.version
        )

        if (
            VulnerabilityScanner.ANTIVIRUS_SCAN
            and plugin_data.plugin_type in job_types
            and plugin_data.plugin_type != "kubeflow"
            and self.docker.clamav_antivirus_scan(
                f"{VulnerabilityScanner.ABSOLUTE_CODE_STORE_PATH}/{plugin_data.name}/{plugin_data.plugin_id}",
                plugin_data.name,
                plugin_data.plugin_id,
            )
        ):
            logging.info("Antivirus scan complete")
            result, data = self.docker.antivirus_report(folder_path=f"/{plugin_data.name}/{plugin_data.plugin_id}")
            if result:
                logging.info("Antivirus scan report generated")
                if data.get("Infected files") != "0":
                    plugin_data.errors.append("Infected files found in the plugin.")
                    plugin_data.deployment_status = "failed"
                    self.plugin_db_conn.update_plugin(
                        plugin_data.plugin_id, {"status": "Antivirus Scan Failed"}, version=plugin_data.version
                    )
                    vulnerability_scan_report = VulnerablityScanReport(project_id=self.project_id)
                    vulnerability_scan_report.update_record(plugin_data.plugin_id, {"antivirus": data})
                else:
                    logging.info("No infected files found")
                    plugin_data.security_checks.antivirus = True
                    self.plugin_db_conn.update_plugin(
                        plugin_data.plugin_id,
                        {
                            "security_checks": plugin_data.security_checks.model_dump(),
                            "status": SCANNING_PROGRESS,
                        },
                        version=plugin_data.version,
                    )
            else:
                logging.info(antivirus_scan_failed)
                plugin_data.errors.append(antivirus_scan_failed)
                plugin_data.deployment_status = "failed"
                plugin_data.security_checks.antivirus = False
                self.plugin_db_conn.update_plugin(
                    plugin_data.plugin_id, {"status": "Antivirus Scan Failed"}, version=plugin_data.version
                )
                raise AntiVirusScanFailed(antivirus_scan_failed)
        else:
            logging.info("Skipping antivirus scan")
            plugin_data.security_checks.antivirus = True
            self.plugin_db_conn.update_plugin(
                plugin_data.plugin_id,
                {"security_checks": plugin_data.security_checks.model_dump()},
                version=plugin_data.version,
            )
            self.plugin_db_conn.update_plugin(
                plugin_data.plugin_id, {"status": SCANNING_PROGRESS}, version=plugin_data.version
            )

    def sonarqube_scan(self, plugin_data: PluginMetaDBSchema):
        self.plugin_db_conn.update_plugin(
            plugin_data.plugin_id, {"status": SCANNING_PROGRESS}, version=plugin_data.version
        )
        if (
            VulnerabilityScanner.SONARQUBE_SCAN
            and plugin_data.plugin_type in job_types
            and plugin_data.plugin_type != "kubeflow"
        ):
            sonar_scan_report = []
            logging.info("Sonarqube scan started")
            sonarqube_scan = SonarQubeScan(project=plugin_data.name)
            sonarqube_scan.initialize_project(
                src_folder=f"{VulnerabilityScanner.ABSOLUTE_CODE_STORE_PATH}/{plugin_data.name}/{plugin_data.plugin_id}"
            )
            report = sonarqube_scan.get_values()

            if report.get("code_smells").get("total") > SonarQubeConfig.code_smell_threshold:
                plugin_data.errors.append("Code smells found in the plugin, exceeding threshold.")
                logging.info("Code smells found in the plugin.")
                sonar_scan_report.extend(sonarqube_scan.sonarqube_code_smells_report(report.get("code_smells")))

            if report.get("vulnerabilities").get("total") > SonarQubeConfig.vulnerability_threshold:
                plugin_data.errors.append("Vulnerabilities found in the plugin, exceeding threshold.")
                logging.info("Vulnerabilities found in the plugin.")
                sonar_scan_report.extend(sonarqube_scan.sonarqube_vulnerabilities_report(report.get("vulnerabilities")))
                self.plugin_db_conn.update_plugin(
                    plugin_data.plugin_id, {"status": "Sonarqube Scan Failed"}, version=plugin_data.version
                )

            if report.get("bug").get("total") > SonarQubeConfig.bug_threshold:
                plugin_data.errors.append("Bugs found in the plugin, exceeding threshold.")
                logging.info("Bugs found in the plugin.")
                sonar_scan_report.extend(sonarqube_scan.sonarqube_bug_report(report.get("bug")))

            if sonar_scan_report:
                vulnerability_scan_report = VulnerablityScanReport(project_id=self.project_id)
                vulnerability_scan_report.update_record(plugin_data.plugin_id, {"sonarqube": sonar_scan_report})
                plugin_data.deployment_status = "failed"
                plugin_data.security_checks.sonarqube = False
                self.plugin_db_conn.update_plugin(
                    plugin_data.plugin_id, {"status": "Sonarqube Scan Failed"}, version=plugin_data.version
                )
                raise SonarqubeScanFailed("Sonarqube scan failed")
            else:
                logging.info("No code smells, vulnerabilities or bugs found")
                plugin_data.security_checks.sonarqube = True
                self.plugin_db_conn.update_plugin(
                    plugin_data.plugin_id,
                    {"security_checks": plugin_data.security_checks.model_dump(), "status": SCANNING_PROGRESS},
                    version=plugin_data.version,
                )
        else:
            logging.info("Skipping sonarqube scan")
            plugin_data.security_checks.sonarqube = True
            self.plugin_db_conn.update_plugin(
                plugin_data.plugin_id,
                {"security_checks": plugin_data.security_checks.model_dump(), "status": SCANNING_PROGRESS},
                version=plugin_data.version,
            )

        return plugin_data

    def configure_kubeflow_pipeline(  # NOSONAR
        self, plugin_data: PluginMetaDBSchema, user_details: MetaInfoSchema, folder_path
    ):
        self.plugin_db_conn.update_plugin(
            plugin_data.plugin_id, {"status": DEPLOYMENT_STARTED}, version=plugin_data.version
        )
        try:
            if not Services.KUBEFLOW_URL:
                raise KubeflowPipelineConfigNotFound(kubeflow_url_not_found)
            if Services.KUBEFLOW_MULTI_USER:
                namespace = user_details.project_id.replace("_", "-")
            else:
                namespace = "kubeflow"
            self.kubeflow_client = kfp.Client(
                host=Services.KUBEFLOW_URL,
                cookies=f"login-token={user_details.login_token}",
                namespace=namespace,
            )
            pipeline_version_id = None

            pipeline_config = {
                config.get("key"): config.get("value")
                for config in plugin_data.configurations
                if config.get("type") == "text"
            }
            deployment_yaml = pipeline_config.get("deployment_yaml") or PIPELINE_YML_FILENAME

            if not os.path.exists(f"{folder_path}/{deployment_yaml}"):
                raise KubeflowPipelineConfigNotFound(
                    f"Pipeline configuration file not found: {folder_path}/{deployment_yaml}"
                )

            pipeline_version_name = f"{plugin_data.name}-{plugin_data.version}"

            if pipeline_id := self.get_kubeflow_pipeline_id(plugin_data.name, self.kubeflow_client, namespace):
                pipeline_list = self.kubeflow_client.list_pipeline_versions(pipeline_id=pipeline_id, page_size=100)
                if pipeline_list.pipeline_versions:
                    for each_version in pipeline_list.pipeline_versions:
                        if each_version.display_name == pipeline_version_name:
                            self.kubeflow_client.delete_pipeline_version(
                                pipeline_id=pipeline_id,
                                pipeline_version_id=each_version.pipeline_version_id,
                            )
                result = self.kubeflow_client.upload_pipeline_version(
                    pipeline_package_path=f"{folder_path}/{deployment_yaml}",
                    pipeline_version_name=pipeline_version_name,
                    pipeline_id=pipeline_id,
                )
                pipeline_version_id = result.pipeline_version_id
            else:
                pipeline = self.kubeflow_client.upload_pipeline(
                    pipeline_package_path=f"{folder_path}/{deployment_yaml}",
                    pipeline_name=plugin_data.name,
                    namespace=namespace,
                )
                pipeline_id = pipeline.pipeline_id
                pipeline_version_id = (
                    self.kubeflow_client.list_pipeline_versions(pipeline_id=pipeline_id, page_size=100)
                    .pipeline_versions[0]
                    .pipeline_version_id
                )
            experiment = self.kubeflow_client.create_experiment(
                name=plugin_data.name,
                namespace=namespace,
            )
            get_recurring_runs = self.kubeflow_client.list_recurring_runs(
                experiment_id=experiment.experiment_id, page_size=100
            )
            if get_recurring_runs.recurring_runs:
                runs_list = get_recurring_runs.recurring_runs
                for each_run in runs_list:
                    if each_run.display_name == plugin_data.name:
                        self.kubeflow_client.disable_recurring_run(each_run.recurring_run_id)

            if os.path.exists(f"{folder_path}/variables.yml"):
                with open(f"{folder_path}/variables.yml") as yaml_file:
                    yaml_data = yaml.load(yaml_file, Loader=yaml.FullLoader)
                pipeline_param = {
                    each.get("name"): each.get("value")
                    for each in yaml_data.get("deployment", []).get("environmentVar", [])
                    if "valueFrom" not in list(each.keys())
                }
                pipeline_params = {"pipeline_param": pipeline_param}
            else:
                pipeline_params = {}
            pipeline_params |= copy.deepcopy(pipeline_config)
            pipeline_params.pop("RECURRING_RUN", None)
            pipeline_params.pop("CRON_EXPRESSION", None)
            pipeline_params.pop("INTERVAL_SECONDS", None)
            logging.info(f"pipeline_config : {pipeline_config}")
            logging.info(f"pipeline params : {pipeline_params}")
            if pipeline_config.get("RECURRING_RUN") in ["true", True, "True"]:
                if not pipeline_config.get("CRON_EXPRESSION") and not pipeline_config.get("INTERVAL_SECONDS"):
                    raise CRONExpressionError("Cron expression or Interval Seconds needs to be set for Recurring Runs")
                response = self.kubeflow_client.create_recurring_run(
                    experiment_id=experiment.experiment_id,
                    job_name=plugin_data.name,
                    pipeline_id=pipeline_id,
                    interval_second=(
                        int(pipeline_config.get("INTERVAL_SECONDS"))
                        if pipeline_config.get("INTERVAL_SECONDS")
                        else None
                    ),
                    cron_expression=(
                        None if pipeline_config.get("INTERVAL_SECONDS") else pipeline_config.get("CRON_EXPRESSION")
                    ),
                    params=pipeline_params,
                    version_id=pipeline_version_id,
                )
                run_id = response.recurring_run_id
            else:
                response = self.kubeflow_client.run_pipeline(
                    experiment.experiment_id,
                    plugin_data.name,
                    pipeline_id=pipeline_id,
                    version_id=pipeline_version_id,
                    params=pipeline_params,
                )
                run_id = response.run_id

            push_notification(
                user_id=user_details.user_id,
                notification=NotificationSchema(
                    message=f"Plugin: {plugin_data.name} has been deployed successfully",
                    plugin_type=plugin_data.plugin_type,
                    plugin_id=plugin_data.plugin_id,
                ),
                project_id=self.project_id,
            )

            return run_id

        except Exception as e:
            self.plugin_db_conn.update_plugin(
                plugin_data.plugin_id, {"status": DEPLOYMENT_FAILED}, version=plugin_data.version
            )
            logging.error(f"Exception occurred in the configure_pipeline due to {str(e)}")
            push_notification(
                user_id=user_details.user_id,
                notification=NotificationSchema(
                    message=f"Plugin: {plugin_data.name} deployment failed",
                    plugin_type=plugin_data.plugin_type,
                ),
                project_id=self.project_id,
            )
            raise e

    def get_run_status(self, user_details: MetaInfoSchema, run_id, namespace: str):
        if not Services.KUBEFLOW_URL:
            raise KubeflowPipelineConfigNotFound(kubeflow_url_not_found)

        self.kubeflow_client = kfp.Client(
            host=Services.KUBEFLOW_URL,
            cookies={"login-token": user_details.login_token},
            namespace=namespace,
        )
        if run := self.kubeflow_client.get_run(run_id=run_id):
            run_status = run.state
            logging.info(f"Run Status: {run_status}")
            return run_status

        else:
            logging.error("Run not found")
            return None

    def get_kubeflow_pipeline_id(self, pipeline_name, kubeflow_client: kfp.Client, namespace):
        try:
            all_pipelines = []

            condition = {
                "predicates": [
                    {
                        "operation": "EQUALS",
                        "key": "display_name",
                        "stringValue": pipeline_name,
                    }
                ]
            }
            page_token = ""
            while True:
                response = kubeflow_client.list_pipelines(
                    namespace=namespace,
                    page_token=page_token,
                    filter=json.dumps(condition),
                )

                all_pipelines.extend(response.pipelines)

                if response.next_page_token:
                    page_token = response.next_page_token
                else:
                    break

            pipeline_id = all_pipelines[0].pipeline_id or None
            return pipeline_id
        except Exception as e:
            logging.exception(f"Unable to get the pipeline Id {e}")

    def delete_kubeflow_pipeline(self, pipeline_name, user_details: MetaInfoSchema):
        try:
            if not Services.KUBEFLOW_URL:
                raise KubeflowPipelineConfigNotFound(kubeflow_url_not_found)
            if Services.KUBEFLOW_MULTI_USER:
                namespace = user_details.project_id.replace("_", "-")
            else:
                namespace = "kubeflow"
            self.kubeflow_client = kfp.Client(
                host=Services.KUBEFLOW_URL,
                cookies=f"login-token={user_details.login_token}",
                namespace=namespace,
            )
            if pipeline_id := self.get_kubeflow_pipeline_id(pipeline_name, self.kubeflow_client, namespace):
                pipeline_version_id_list = self.get_pipeline_version_ids(pipeline_id, self.kubeflow_client)
                self.delete_recurring_runs(
                    self.kubeflow_client,
                    pipeline_id,
                    pipeline_version_id_list,
                    namespace,
                )
                self.delete_pipeline_versions(self.kubeflow_client, pipeline_id, pipeline_version_id_list)
                self.kubeflow_client.delete_pipeline(pipeline_id)
                logging.info(f"Successfully deleted the pipeline - {pipeline_id}")

        except Exception as e:
            logging.exception(f"Unable to delete kubeflow pipeline, {e}")
            raise e

    def get_pipeline_version_ids(self, pipeline_id, kubeflow_client: kfp.Client):
        pipeline_version_id_list = []

        pipeline_list = kubeflow_client.list_pipeline_versions(pipeline_id=pipeline_id, page_size=100)
        if pipeline_list.pipeline_versions:
            for each_version in pipeline_list.pipeline_versions:
                pipeline_version_id_list.append(each_version.pipeline_version_id)
        return pipeline_version_id_list

    def delete_runs(
        self,
        kubeflow_client: kfp.Client,
        pipeline_id,
        pipeline_version_id_list,
        namespace: str,
    ):
        runs = kubeflow_client.list_runs(namespace=namespace, experiment_id=self.experiment.experiment_id)
        for each_run in runs.runs:
            if (
                each_run.pipeline_version_reference.pipeline_id == pipeline_id
                and each_run.pipeline_version_reference.pipeline_version_id in pipeline_version_id_list
            ):
                kubeflow_client.delete_run(run_id=each_run.run_id)
                logging.info(f"Successfully deleted the run - {each_run.run_id}")

    def delete_pipeline_versions(self, kubeflow_client: kfp.Client, pipeline_id, pipeline_version_id_list):
        for each_version in pipeline_version_id_list:
            kubeflow_client.delete_pipeline_version(pipeline_id=pipeline_id, pipeline_version_id=each_version)
            logging.info(f"Successfully deleted the pipeline version- {each_version}")

    def delete_recurring_runs(
        self,
        kubeflow_client: kfp.Client,
        pipeline_id,
        pipeline_version_id_list,
        namespace: str,
    ):
        all_recurring_runs = []
        page_token = ""

        while True:
            recurring_runs = kubeflow_client.list_recurring_runs(namespace=namespace, page_token=page_token)
            if recurring_runs.recurring_runs:
                all_recurring_runs.extend(recurring_runs.recurring_runs)
            if recurring_runs.next_page_token:
                page_token = recurring_runs.next_page_token
            else:
                break

        for each_recurring_run in all_recurring_runs:
            if (
                each_recurring_run.pipeline_version_reference.pipeline_id == pipeline_id
                and each_recurring_run.pipeline_version_reference.pipeline_version_id in pipeline_version_id_list
            ):
                kubeflow_client.delete_recurring_run(recurring_run_id=each_recurring_run.recurring_run_id)
                logging.info(f"Successfully deleted the recurring run - {each_recurring_run.recurring_run_id}")

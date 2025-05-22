import logging
import os
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Request,
    Response,
    UploadFile,
    HTTPException,
)
from fastapi.responses import FileResponse
from ut_security_util import MetaInfoSchema, create_token
from scripts.utils.rbac import RBAC

from scripts.config import PathConf, ResourceConfig, Secrets, DownloadDockerImage
from scripts.constants import APIEndPoints, Message
from scripts.core.engines.plugin_deployment_engines.widget import (
    DeploymentEngine as WidgetPlEngine,
)
from scripts.errors import ContentTypeError, ILensErrors, VerficiationError
from scripts.services.v1.handler import DeploymentHandler, PluginHandler
from scripts.services.v1.schemas import (
    ConfigurationSave,
    DefaultFailureResponse,
    DefaultResponse,
    DeployPlugin,
    LoadConfigRequest,
    Plugin,
    PluginListRequest,
    SwitchPluginState,
    DeletePlugins,
    PluginDownloadRequest,
)
from scripts.utils.decorators import validate_deco

router = APIRouter(prefix=APIEndPoints.plugin_services_base, tags=["v1 | Plugin APIs"])


@router.post(APIEndPoints.plugin_save)
def save_plugin(
    user_details: MetaInfoSchema,
    plugin_data: Plugin,
    bg_task: BackgroundTasks,
    rbac_permissions: dict = Depends(RBAC(entity_name="developerPlugins", operation=["create", "edit"])),
):
    """
    The save_plugin function is used to create a new plugin or edit a existing one.

    """
    try:
        handler = PluginHandler(user_details.project_id)
        data = handler.create_plugin(plugin_data=plugin_data, bg_task=bg_task, rbac_permissions=rbac_permissions)
        return DefaultResponse(message="Plugin created successfully", data=data)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.post(APIEndPoints.plugin_list, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))])
def list_plugins(user_details: MetaInfoSchema, list_request: PluginListRequest):
    """
    The list_plugins function is used to list all the plugins in a project.

    """
    try:
        handler = PluginHandler(user_details.project_id)
        data = handler.list_plugins(list_request)
        return DefaultResponse(message="Plugin listed successfully", data=data)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(APIEndPoints.plugin_fetch, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))])
def get_plugin(user_details: MetaInfoSchema, plugin_id: str, version: float):
    """
    The get_plugin function is used to fetch details of a plugin.

    """
    try:
        handler = PluginHandler(user_details.project_id)
        if data := handler.get_plugin(plugin_id, version):
            return DefaultResponse(message="Plugin fetched successfully", data=data)
        else:
            return DefaultResponse(message=Message.plugin_not_found)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.delete(
    APIEndPoints.plugin_delete, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["delete"]))]
)
def delete_plugin(user_details: MetaInfoSchema, request_data: DeletePlugins, bg_task: BackgroundTasks):
    """
    The delete_plugin function deletes multiple plugins from the project.

    """
    results = []
    plugin_ids = request_data.plugin_ids if isinstance(request_data.plugin_ids, list) else [request_data.plugin_ids]
    handler = PluginHandler(user_details.project_id)

    try:
        for plugin_id in plugin_ids:
            data = handler.delete_plugin(plugin_id, bg_task=bg_task, user_details=user_details)
        return DefaultResponse(message="Plugin deleted successfully", data=data)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))

    return DefaultResponse(message="Plugins deletion completed", data=results)


@router.post(
    APIEndPoints.update_configuration,
    dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["edit", "create"]))],
    include_in_schema=False,
)
def save_configurations(user_details: MetaInfoSchema, configuration_req: ConfigurationSave):
    try:
        handler = PluginHandler(user_details.project_id)
        data = handler.save_configurations(
            plugin_id=configuration_req.plugin_id,
            configurations=configuration_req.configurations,
        )
        return DefaultResponse(message="Configuration updated successfully", data=data)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.post(
    APIEndPoints.plugin_deploy,
    dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["create", "edit"]))],
)
@validate_deco
def deploy_plugin(
    user_details: MetaInfoSchema,
    plugin_data: DeployPlugin,
    bg_task: BackgroundTasks,
    request: Request,
    response: Response,
):
    """
    The deploy_plugin function is used to deploy a plugin.

    """
    _ = request
    _ = response
    try:
        logging.debug("Deployment Started in API")
        handler = DeploymentHandler(user_details.project_id)
        handler.deploy_plugin(plugin_data=plugin_data, user_details=user_details, bg_task=bg_task)
        return DefaultResponse(message="Plugin deployment started")
    except VerficiationError as ve:
        return DefaultFailureResponse(message=ve.message)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.post(
    APIEndPoints.upload_files,
    dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["edit", "create"]))],
)
def upload(
    user_details: MetaInfoSchema,
    plugin_id: Annotated[str, Form()],
    files: list[UploadFile] = File(...),
):
    """
    The upload function is used to upload files related to a plugin.

    """
    try:
        handler = PluginHandler(project_id=user_details.project_id)
        handler.upload_files(plugin_id=plugin_id, files=files)
        return {"message": f"Successfully uploaded {[file.filename for file in files]}"}
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.get_uploaded_files, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))]
)
def get_uploaded_files(user_details: MetaInfoSchema, plugin_id: str):
    """
    The get_uploaded_files function returns a list of uploaded files for the given plugin.

    """
    try:
        handler = PluginHandler(project_id=user_details.project_id)
        data = handler.get_uploaded_files(plugin_id=plugin_id)
        return DefaultResponse(message="Plugin fetched successfully", data=data)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.download_uploaded_files,
    dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))],
)
def download_uploaded_files(user_details: MetaInfoSchema, plugin_id: str, file_name: str):
    """
    The download_uploaded_files function downloads the uploaded files from a plugin.

    """
    try:
        handler = PluginHandler(project_id=user_details.project_id)
        return handler.download_uploaded_files(plugin_id=plugin_id, file_name=file_name)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(APIEndPoints.get_errors, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))])
def get_errors(user_details: MetaInfoSchema, plugin_id: str):
    """
    The get_errors function is used to fetch the errors of a plugin.

    """
    try:
        handler = PluginHandler(project_id=user_details.project_id)
        data = handler.get_errors(plugin_id=plugin_id)
        return DefaultResponse(message="Errors fetched successfully", data=data)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(APIEndPoints.get_info, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))])
def get_info(request: Request, user_details: MetaInfoSchema, plugin_id: str, version: float):
    """
    The get_info function is used to get limited info a  plugin.

    """
    try:
        host = request.headers.get("referer", "").rstrip("/")
        handler = PluginHandler(project_id=user_details.project_id)
        data = handler.get_info(plugin_id=plugin_id, version=version, host=host)
        return DefaultResponse(message="Plugin info fetched successfully", data=data)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(APIEndPoints.plugin_logs, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))])
def get_plugin_logs(user_details: MetaInfoSchema, plugin_id: str, version: float):
    """
    The get_plugin_logs function is used to fetch the logs of a plugin.

    """
    try:
        handler = PluginHandler(project_id=user_details.project_id)
        if not handler.status_check(plugin_id=plugin_id, version=version):
            return DefaultFailureResponse(message="Plugin Logs Not Found")
        data = handler.get_plugin_logs(plugin_id=plugin_id, version=version)
        return DefaultResponse(message="Plugin logs fetched successfully", data=data)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.post(APIEndPoints.api_save_refresh_load_conf, include_in_schema=False)
def update_save_load_config(user_details: MetaInfoSchema, plugin_data: LoadConfigRequest):
    try:
        handler = WidgetPlEngine(project_id=user_details.project_id)
        cookies = {
            "login-token": create_token(
                project_id=user_details.project_id,
                user_id=user_details.user_id,
                ip=user_details.ip_address,
                token=Secrets.token,
            )
        }
        resp = handler.save_meta_data(plugin_id=plugin_data.plugin_id, cookies=cookies)
        if resp:
            return DefaultResponse(message="Meta Configuration Updated Successfully", data={"status": resp})
        else:
            return DefaultFailureResponse(message="Failed to Update the Meta Configuration", data={"status": resp})
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.plugin_logs_download, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))]
)
def download_plugin_logs(user_details: MetaInfoSchema, plugin_id: str):
    """
    The download_plugin_logs function downloads the logs of a plugin.

    """
    try:
        handler = PluginHandler(project_id=user_details.project_id)
        return handler.download_plugin_logs(plugin_id=plugin_id)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.post(
    APIEndPoints.plugin_state,
    dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["create", "edit"]))],
)
def switch_plugin_state(user_details: MetaInfoSchema, request_data: SwitchPluginState, bg_task: BackgroundTasks):
    """
    The switch_plugin_state function is used to start or stop plugins.

    """
    try:
        handler = DeploymentHandler(project_id=user_details.project_id)
        plugin_ids = request_data.plugin_ids if isinstance(request_data.plugin_ids, list) else [request_data.plugin_ids]
        for plugin_id in plugin_ids:
            try:
                message = handler.start_stop_plugin(plugin_id=plugin_id, bg_task=bg_task)
                return DefaultResponse(message=message, data=None)
            except Exception as e:
                logging.exception(e)
                return DefaultFailureResponse(message="Failed", error=str(e))
        return DefaultResponse(message="Plugin state switch completed", data=None)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.plugin_report, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))]
)
def get_plugin_report(user_details: MetaInfoSchema, plugin_id: str):
    """
    The get_plugin_report function returns the security scan reports of a plugin.

    """
    try:
        handler = PluginHandler(project_id=user_details.project_id)
        data = handler.get_plugin_report(plugin_id=plugin_id)
        return DefaultResponse(message="Plugin report fetched successfully", data=data)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.plugin_report_download,
    dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))],
)
def download_plugin_report(user_details: MetaInfoSchema, plugin_id: str):
    """
    The download_plugin_report function downloads the report of a plugin as an excel sheet.

    """
    try:
        handler = PluginHandler(project_id=user_details.project_id)
        return handler.download_plugin_report(plugin_id=plugin_id)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.resource_config,
    dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))],
    include_in_schema=False,
)
def get_resource_config(user_details: MetaInfoSchema):
    try:
        return DefaultResponse(message="Resource config fetched successfully", data=ResourceConfig.__dict__)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.plugin_advance_config, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))]
)
def get_plugin_advance_config(user_details: MetaInfoSchema):
    """
    The get_plugin_advance_config function is used to get the advanced configurations for plugins.

    """
    try:
        plugin_handler = PluginHandler(project_id=user_details.project_id)
        data = plugin_handler.get_plugin_advance_config()
        return DefaultResponse(message="Plugin advance config fetched successfully", data=data)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)


@router.get(
    APIEndPoints.plugin_headercontent,
    dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))],
    include_in_schema=False,
)
def get_plugin_headercontent(
    user_details: MetaInfoSchema,
    rbac_permissions: dict = Depends(
        RBAC(entity_name="developerPlugins", operation=["create", "edit", "delete", "view"])
    ),
    portal: bool = False,
):
    try:
        plugin_handler = PluginHandler(project_id=user_details.project_id)
        header_content = plugin_handler.get_plugin_list_table_header_based_on_portal(rbac_permissions, portal)
        return DefaultResponse(
            message="Fetched Table Header",
            data=header_content,
        )
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.plugin_securuty_check, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))]
)
def get_plugin_security_check(user_details: MetaInfoSchema, plugin_id: str, version: float):
    """
    The get_plugin_security_check function is used to get the security check list of a plugin.

    """
    try:
        plugin_handler = PluginHandler(project_id=user_details.project_id)
        return DefaultResponse(
            message="Fetched Security Check",
            data=plugin_handler.get_plugin_security_check(plugin_id=plugin_id, version=version),
        )
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(APIEndPoints.plugin_list_by_type)
def list_plugins_by_type(user_details: MetaInfoSchema, category: str):
    """
    The list_plugins_by_type function is used to list plugins by category (formio components or custom app).
    """
    try:
        handler = PluginHandler(user_details.project_id)
        data = handler.list_plugins_by_type(plugin_type=category)
        return DefaultResponse(message="Plugin listed successfully", data=data)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.plugin_details, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))]
)
def get_plugin_details(user_details: MetaInfoSchema, plugin_id: str):
    """
    The get_plugin_details function fetches the plugin details for a given project, for plugin types widget, formio component and custom app.
    """
    try:
        handler = PluginHandler(user_details.project_id)
        data = handler.fetch_plugin_details(plugin_id=plugin_id)
        return DefaultResponse(message="Plugin details fetched successfully", data=data)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.plugin_env_config, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))]
)
def get_plugin_env_config(user_details: MetaInfoSchema):
    """
    The get_plugin_env_config function fetches configurable environment variable types for a plugin.
    """
    try:
        handler = PluginHandler(user_details.project_id)
        data = handler.fetch_plugin_env_config()
        return DefaultResponse(message="Plugin env config fetched successfully", data=data)
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.post(
    APIEndPoints.plugin_v2_bundle_upload,
    dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["create", "edit"]))],
)
async def upload_bundle_v2(
    user_details: MetaInfoSchema,
    plugin_id: Annotated[str, Form()],
    files: UploadFile = File(...),
    chunk_number: int = Form(...),
    total_chunks: int = Form(...),
    file_name: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    The upload_bundle function is used to upload zip file for a plugin for registration type Bundle Upload.
    """
    try:
        progress = (chunk_number / total_chunks) * 100
        handler = PluginHandler(project_id=user_details.project_id)
        await handler.upload_files_to_minio_v2(
            plugin_id=plugin_id, file=files, file_name=file_name, bg=background_tasks
        )
        return DefaultResponse(message=Message.bundle_message, data={"progress": progress})
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.post(
    APIEndPoints.plugin_bundle_upload,
    dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["create", "edit"]))],
)
def upload_bundle(
    user_details: MetaInfoSchema,
    plugin_id: Annotated[str, Form()],
    version: Annotated[float, Form()],
    files: UploadFile = File(...),
):
    """
    The upload_bundle function is used to upload zip file for a plugin for registration type Bundle Upload.
    """
    try:
        handler = PluginHandler(project_id=user_details.project_id)
        path = handler.upload_files_to_minio(
            plugin_id=plugin_id, file=files, version=version, user_details=user_details
        )
        return DefaultResponse(message=Message.bundle_message, data=path)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.post("/finalize-upload/")
def finalize_upload(user_details: MetaInfoSchema, file_name: str = Form(...), plugin_id: str = Form(...)):
    try:
        handler = PluginHandler(project_id=user_details.project_id)
        path = handler.push_to_minio(plugin_id=plugin_id, file_name=file_name)
        return DefaultResponse(message=Message.bundle_message, data={"path": path})
    except ContentTypeError as e:
        logging.exception("File format not supported: {e}")
        return DefaultFailureResponse(message="File format not supported", error=str(e))
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.plugin_bundle_download,
    dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))],
)
def download_bundle(user_details: MetaInfoSchema, plugin_id: str):
    """
    The download_bundle function is used to download the uploaded bundle for a plugin.
    """
    try:
        handler = PluginHandler(project_id=user_details.project_id)
        file_path = None
        if file_path := handler.download_plugin_bundle(plugin_id=plugin_id):
            return FileResponse(file_path, filename=file_path.split("/")[-1])
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))
    finally:
        if file_path:
            os.remove(file_path)


@router.post(
    APIEndPoints.download_docker_image, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))]
)
def download_docker_image(
    user_details: MetaInfoSchema, request: PluginDownloadRequest, background_tasks: BackgroundTasks
):
    """
    The download_docker_image function is used to download Docker images for plugins.
    """
    try:
        if request.portal:
            DownloadDockerImage.DOWNLOAD_IMAGE_ENABLED = True
        if not DownloadDockerImage.DOWNLOAD_IMAGE_ENABLED:
            raise HTTPException(status_code=401, detail="Download Artifact is not allowed")
        for plugin_id in request.plugin_ids:
            handler = PluginHandler(user_details.project_id)
            plugin_data = handler.get_plugin(plugin_id, request.version)
            if not plugin_data:
                raise HTTPException(status_code=404, detail=Message.plugin_not_found)

            local_image_dir = PathConf.LOCAL_IMAGE_PATH / f"{plugin_data.name}"
            local_image_path = local_image_dir / "plugin.tar"
            if local_image_path.exists():
                os.remove(local_image_path)
                logging.info(f"Deleted existing tar file: {local_image_path}")

            if plugin_data.plugin_type != "kubeflow":
                background_tasks.add_task(handler.docker_image_download, plugin_data, plugin_id, user_details)
            else:
                background_tasks.add_task(handler.docker_image_download_kubeflow, plugin_data, plugin_id, user_details)

        return DefaultResponse(message="Download in progress. You will be notified once it is complete.")
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.download_file, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))]
)
def download_file(user_details: MetaInfoSchema, plugin_id: str, version: str | float):
    """
    Serve the downloaded file based on the plugin ID.
    """
    handler = PluginHandler(user_details.project_id)
    plugin_data = handler.get_plugin(plugin_id, float(version))
    if not plugin_data:
        raise HTTPException(status_code=404, detail=Message.plugin_not_found)

    local_image_dir = PathConf.LOCAL_IMAGE_PATH / f"{plugin_data.name}.zip"

    if local_image_dir.exists():
        return FileResponse(
            local_image_dir,
            media_type="application/zip",
            filename=os.path.basename(local_image_dir),
        )
    raise HTTPException(status_code=404, detail="File not found")


@router.get(
    APIEndPoints.fetch_versions, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))]
)
def fetch_versions(user_details: MetaInfoSchema, plugin_id: str):
    """
    The fetch_versions function is used to fetch the versions of a plugin.
    """
    try:
        handler = PluginHandler(project_id=user_details.project_id)
        formatted_data = handler.fetch_versions(plugin_id=plugin_id)
        return {"status": "success", "message": "success", "data": formatted_data}
    except ILensErrors as ile:
        return DefaultFailureResponse(message=ile.message)
    except Exception as e:
        return DefaultFailureResponse(message="Failed", error=str(e))

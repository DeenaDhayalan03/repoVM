from fastapi import APIRouter
from fastapi.responses import JSONResponse

from scripts.exceptions import (
    DeploymentException,
    ServiceException,
    VirtualServiceException,
)
from scripts.handlers.kubernetes_handler import KubernetesHandler
from scripts.logging import logger
from scripts.schema import DeleteConfig, DeployConfig, DeploymentStatus, PodStatus

router = APIRouter()


@router.post("/deploy")
def plugin(deploy_config: DeployConfig):
    try:
        kubernetes_handler = KubernetesHandler(deploy_config)
        deployment, service, virtual_service = kubernetes_handler.create_deployment()
        return JSONResponse(
            status_code=200,
            content={
                "message": "Resource created successfully",
                "deployment": deployment,
                "service": service,
                "proxy-path": virtual_service,
            },
        )
    except DeploymentException as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Deployment failed for {kubernetes_handler.name} with error: {e}"},
        )
    except ServiceException as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Service creation failed for {kubernetes_handler.name} with error: {e}"},
        )
    except VirtualServiceException as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Virtual service creation failed for {kubernetes_handler.name} with error: {e}"},
        )

    except Exception as e:
        logger.error(f"Unexpected error during plugin deployment: {e}")
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@router.post("/delete-resource")
def delete_resource(delete_conf: DeleteConfig):
    try:
        kubernetes_handler = KubernetesHandler()
        deployment, service, virtual_service = kubernetes_handler.delete_deployment(delete_conf)
        return JSONResponse(
            status_code=200,
            content={
                "message": "Resource deleted successfully",
                "deployment": deployment,
                "service": service,
                "proxy-path": virtual_service,
            },
        )

    except DeploymentException as e:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Deployment deletion failed for {delete_conf.app_name}-{delete_conf.app_id} with error: {e}"
            },
        )
    except ServiceException as e:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Service deletion failed for {delete_conf.app_name}-{delete_conf.app_id} with error: {e}"
            },
        )
    except VirtualServiceException as e:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Virtual service deletion failed for {delete_conf.app_name}-{delete_conf.app_id} with error: {e}"
            },
        )

    except Exception as e:
        logger.error(f"Unexpected error during plugin deployment: {e}")
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@router.post("/status")
def deployment_status(status_config: PodStatus):
    try:
        kubernetes_handler = KubernetesHandler()
        status = kubernetes_handler.deployment_status(status_config)
        return JSONResponse(status_code=200, content={"message": status})
    except Exception as e:
        logger.error(f"Unexpected error during plugin deployment: {e}")
        return JSONResponse(
            status_code=404,
            content={"detail": f"Resources not found for {kubernetes_handler.name}"},
        )


@router.post("/deployment-status")
async def deployments_status(deployments: DeploymentStatus):
    try:
        kubernetes_handler = KubernetesHandler()
        status = await kubernetes_handler.deployments_status(deployments.plugin_list)
        return JSONResponse(
            status_code=200,
            content={
                "message": "Deployment statuses",
                "status": "success",
                "data": status,
            },
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        logger.error(f"Unexpected error during plugin deployment: {e}")
        return JSONResponse(
            status_code=404,
            content={
                "data": e.args,
                "status": "failure",
                "message": "Couldn't fetch deployment statuses",
            },
        )


@router.post("/plugin-logs")
def get_plugin_logs(plugin: str, lines: int = 100):
    try:
        kubernetes_handler = KubernetesHandler()
        logs = kubernetes_handler.get_logs(plugin, lines=lines)
        return JSONResponse(
            status_code=200,
            content={
                "message": "Pod logs",
                "status": "success",
                "data": logs,
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error during plugin deployment: {e}")
        return JSONResponse(
            status_code=404,
            content={
                "data": e.args,
                "status": "failure",
                "message": "Couldn't fetch pod logs",
            },
        )


@router.get("/plugin-switch")
def plugin_switch(plugin: str, status: str):
    try:
        kube_handler = KubernetesHandler()
        kube_handler.start_stop_deployment(plugin, status)
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Deployment {status}",
                "status": "success",
                "data": f"Deployment {status}",
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error during plugin deployment: {e}")
        return JSONResponse(
            status_code=404,
            content={
                "data": e.args,
                "status": "failure",
                "message": "Couldn't change deployment status",
            },
        )


@router.get("/secrets")
def get_secrets():
    try:
        kube_handler = KubernetesHandler()
        secrets = kube_handler.get_secrets_from_namespace()
        return JSONResponse(
            status_code=200,
            content={
                "message": "Secrets",
                "status": "success",
                "data": secrets,
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error during plugin deployment: {e}")
        return JSONResponse(
            status_code=404,
            content={
                "data": e.args,
                "status": "failure",
                "message": "Couldn't fetch secrets",
            },
        )

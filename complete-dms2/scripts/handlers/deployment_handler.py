from kubernetes import client, config
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from scripts.models.deployment_model import DeploymentCreateRequest, DeploymentScaleRequest
from scripts.utils.jwt_utils import get_current_user_from_token
from scripts.logging.logger import logger
from scripts.models.jwt_model import TokenData
from scripts.constants.app_constants import (
    DEPLOYMENT_CREATE_SUCCESS,
    DEPLOYMENT_CREATE_FAILURE,
    DEPLOYMENT_DELETE_SUCCESS,
    DEPLOYMENT_DELETE_FAILURE,
    DEPLOYMENT_SCALE_SUCCESS,
    DEPLOYMENT_SCALE_FAILURE,
    DEPLOYMENT_NOT_FOUND,
    DEPLOYMENT_LIST_FAILURE
)

try:
    config.load_incluster_config()
except:
    config.load_kube_config()

apps_v1 = client.AppsV1Api()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="app1/auth/auth/login")


def list_k8s_deployments(current_user: TokenData, namespace: str = "default"):
    try:
        user_id = current_user.username

        deployments = apps_v1.list_namespaced_deployment(namespace=namespace)
        result = []
        for dep in deployments.items:
            result.append({
                "name": dep.metadata.name,
                "namespace": dep.metadata.namespace,
                "replicas": dep.spec.replicas,
                "labels": dep.metadata.labels,
                "containers": [
                    {"name": c.name, "image": c.image} for c in dep.spec.template.spec.containers
                ]
            })
        return result
    except Exception as e:
        logger.error(f"Failed to list deployments: {str(e)}")
        raise HTTPException(status_code=500, detail=DEPLOYMENT_LIST_FAILURE)


def create_k8s_deployment(data: DeploymentCreateRequest, current_user: TokenData):
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

        containers = [
            client.V1Container(
                name=c.name,
                image=c.image,
                ports=[client.V1ContainerPort(container_port=p) for p in (c.ports or [])],
                env=[client.V1EnvVar(name=k, value=v) for k, v in (c.env or {}).items()]
            ) for c in data.containers
        ]

        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=data.name, labels=data.labels),
            spec=client.V1DeploymentSpec(
                replicas=data.replicas,
                selector=client.V1LabelSelector(match_labels=data.labels),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels=data.labels),
                    spec=client.V1PodSpec(containers=containers)
                )
            )
        )

        apps_v1.create_namespaced_deployment(namespace=data.namespace, body=deployment)
        logger.info(f"Deployment '{data.name}' created in namespace '{data.namespace}' by user '{current_user.username}'")
        return {"message": f"{DEPLOYMENT_CREATE_SUCCESS}: '{data.name}'"}

    except Exception as e:
        logger.error(f"Failed to create deployment: {str(e)}")
        raise HTTPException(status_code=500, detail=DEPLOYMENT_CREATE_FAILURE)


def scale_k8s_deployment(namespace: str, name: str, scale: DeploymentScaleRequest, current_user: TokenData):
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

        body = {"spec": {"replicas": scale.replicas}}
        apps_v1.patch_namespaced_deployment_scale(name=name, namespace=namespace, body=body)
        logger.info(f"Scaled deployment '{name}' in namespace '{namespace}' to {scale.replicas} replicas")
        return {"message": f"{DEPLOYMENT_SCALE_SUCCESS}: '{name}' scaled to {scale.replicas} replicas"}

    except client.exceptions.ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=DEPLOYMENT_NOT_FOUND)
        logger.error(f"Kubernetes API error: {e}")
        raise HTTPException(status_code=500, detail=DEPLOYMENT_SCALE_FAILURE)


def delete_k8s_deployment(namespace: str, name: str, current_user: TokenData):
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

        apps_v1.delete_namespaced_deployment(name=name, namespace=namespace)
        logger.info(f"Deleted deployment '{name}' in namespace '{namespace}'")
        return {"message": f"{DEPLOYMENT_DELETE_SUCCESS}: '{name}'"}

    except client.exceptions.ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=DEPLOYMENT_NOT_FOUND)
        logger.error(f"Kubernetes API error: {e}")
        raise HTTPException(status_code=500, detail=DEPLOYMENT_DELETE_FAILURE)

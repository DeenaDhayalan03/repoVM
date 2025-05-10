from kubernetes import client, config
from fastapi import HTTPException, status
from scripts.models.volume_model import VolumeCreateRequest, VolumeRemoveRequest
from scripts.models.jwt_model import TokenData
from scripts.logging.logger import logger
from scripts.constants.app_constants import (
    VOLUME_CREATE_SUCCESS,
    VOLUME_CREATE_FAILURE,
    VOLUME_REMOVE_SUCCESS,
    VOLUME_REMOVE_FAILURE,
    VOLUME_NOT_FOUND,
)
from scripts.constants.app_configuration import settings

try:
    config.load_incluster_config()
except:
    config.load_kube_config()

class VolumeHandler:

    @staticmethod
    def create_volume_with_params(data: VolumeCreateRequest, current_user: TokenData):
        if current_user.role != "admin":
            logger.warning(f"User '{current_user.username}' is not authorized to create volumes")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to create volumes"
            )

        try:
            v1 = client.CoreV1Api()
            pvc_name = data.name

            pvc = client.V1PersistentVolumeClaim(
                metadata=client.V1ObjectMeta(name=pvc_name),
                spec=client.V1PersistentVolumeClaimSpec(
                    access_modes=data.access_modes or ["ReadWriteOnce"],
                    resources=client.V1ResourceRequirements(
                        requests={"storage": data.storage or "1Gi"}
                    ),
                    storage_class_name=data.storage_class_name or None
                )
            )

            v1.create_namespaced_persistent_volume_claim(
                namespace=settings.KANIKO_NAMESPACE,
                body=pvc
            )

            logger.info(f"Created PVC '{pvc_name}' successfully by user '{current_user.username}'")
            return {
                "message": f"{VOLUME_CREATE_SUCCESS}: '{pvc_name}'",
                "name": pvc_name
            }

        except Exception as e:
            logger.error(f"Failed to create PVC: {str(e)}")
            raise HTTPException(status_code=500, detail=VOLUME_CREATE_FAILURE)

    @staticmethod
    def remove_volume_with_params(name: str, params: VolumeRemoveRequest, current_user: TokenData):
        if current_user.role != "admin":
            logger.warning(f"User '{current_user.username}' is not authorized to remove volumes")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to remove volumes"
            )

        try:
            v1 = client.CoreV1Api()
            v1.delete_namespaced_persistent_volume_claim(
                name=name,
                namespace=settings.KANIKO_NAMESPACE
            )
            logger.info(f"Deleted PVC '{name}' successfully by user '{current_user.username}'")
            return {"message": f"{VOLUME_REMOVE_SUCCESS}: '{name}'"}

        except client.exceptions.ApiException as e:
            if e.status == 404:
                logger.warning(f"PVC '{name}' not found")
                raise HTTPException(status_code=404, detail=VOLUME_NOT_FOUND)
            logger.error(f"Kubernetes API error while deleting PVC '{name}': {str(e)}")
            raise HTTPException(status_code=500, detail=VOLUME_REMOVE_FAILURE)

        except Exception as e:
            logger.error(f"Failed to delete PVC '{name}': {str(e)}")
            raise HTTPException(status_code=500, detail=VOLUME_REMOVE_FAILURE)

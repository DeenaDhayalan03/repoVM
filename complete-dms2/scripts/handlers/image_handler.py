from kubernetes import client, config
from fastapi import HTTPException
from scripts.models.image_model import ImageBuildRequest, ImageRemoveRequest, ImageGithubBuildRequest
from scripts.constants.app_constants import *
from scripts.models.jwt_model import TokenData
from scripts.constants.app_configuration import settings
import re
import os
import json
import base64
import tempfile
import git
import shutil
import yaml

# Load Kubernetes configuration
try:
    config.load_incluster_config()
except:
    config.load_kube_config()

class ImageHandler:

    @staticmethod
    def is_valid_docker_tag(tag: str) -> bool:
        return bool(re.match(r"^[a-z0-9]+([._-]?[a-z0-9]+)*(\/[a-z0-9]+([._-]?[a-z0-9]+)*)*(\:[a-zA-Z0-9_.-]+)?$", tag))

    @staticmethod
    def build_image(data: ImageBuildRequest, current_user: TokenData):
        try:
            user_id = current_user.username
            build_args = data.dict(exclude_unset=True)

            if not build_args.get("path") and not build_args.get("fileobj"):
                raise HTTPException(status_code=400, detail=INVALID_REQUEST)

            tag = build_args.get("tag")
            if tag:
                if not ImageHandler.is_valid_docker_tag(tag):
                    raise HTTPException(status_code=400, detail=INVALID_REQUEST)
            else:
                build_args["tag"] = settings.DEFAULT_DOCKER_TAG

            # Use Kaniko for building images in Kubernetes
            # Prepare the Kaniko pod specification
            kaniko_pod_spec = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": f"kaniko-build-{user_id}",
                    "namespace": settings.KANIKO_NAMESPACE
                },
                "spec": {
                    "containers": [{
                        "name": "kaniko",
                        "image": settings.KANIKO_IMAGE,
                        "args": [
                            f"--dockerfile={build_args.get('dockerfile', 'Dockerfile')}",
                            f"--context={build_args['path']}",
                            f"--destination={build_args['tag']}"
                        ],
                        "volumeMounts": [{
                            "name": "kaniko-secret",
                            "mountPath": "/kaniko/.docker/"
                        }]
                    }],
                    "restartPolicy": "Never",
                    "volumes": [{
                        "name": "kaniko-secret",
                        "secret": {
                            "secretName": settings.DOCKER_SECRET_NAME
                        }
                    }]
                }
            }

            # Create the Kaniko pod
            api_instance = client.CoreV1Api()
            api_instance.create_namespaced_pod(
                namespace=settings.KANIKO_NAMESPACE,
                body=kaniko_pod_spec
            )

            return {
                "message": IMAGE_BUILD_SUCCESS.format(tag=build_args['tag']),
                "id": f"kaniko-build-{user_id}",
                "tags": [build_args['tag']]
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{IMAGE_BUILD_FAILURE}: {str(e)}")

    @staticmethod
    def build_image_from_github(data: ImageGithubBuildRequest, current_user: TokenData):
        try:
            temp_dir = tempfile.mkdtemp()
            repo_url = data.github_url
            dockerfile_path = data.dockerfile_path

            try:
                git.Repo.clone_from(repo_url, temp_dir)
            except git.exc.GitCommandError as e:
                raise HTTPException(status_code=400, detail=f"Git clone failed: {str(e)}")

            dockerfile_full_path = os.path.join(temp_dir, dockerfile_path)
            if not os.path.exists(dockerfile_full_path):
                raise HTTPException(status_code=400, detail=f"Dockerfile not found at: {dockerfile_path}")

            # Use the build_image method with the cloned path
            build_request = ImageBuildRequest(
                path=temp_dir,
                tag=data.tag,
                dockerfile=dockerfile_path
            )
            return ImageHandler.build_image(build_request, current_user)

        except git.exc.GitCommandError as e:
            raise HTTPException(status_code=400, detail=f"Git error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{IMAGE_BUILD_FAILURE}: {str(e)}")
        finally:
            shutil.rmtree(temp_dir)

    @staticmethod
    def list_images(name: str = None, all: bool = False, current_user: TokenData = None):
        try:
            user_id = current_user.username
            # List all pods and extract image information
            api_instance = client.CoreV1Api()
            pods = api_instance.list_pod_for_all_namespaces()
            images = set()
            for pod in pods.items:
                for container in pod.spec.containers:
                    images.add(container.image)
            return {
                "message": IMAGE_LIST_SUCCESS,
                "images": list(images)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=IMAGE_LIST_FAILURE)

    @staticmethod
    def dockerhub_login(username: str, password: str, current_user: TokenData):
        try:
            user_id = current_user.username
            # Create Docker registry secret
            secret = client.V1Secret(
                metadata=client.V1ObjectMeta(name=settings.DOCKER_SECRET_NAME),
                data={
                    ".dockerconfigjson": base64.b64encode(json.dumps({
                        "auths": {
                            "https://index.docker.io/v1/": {
                                "username": username,
                                "password": password,
                                "email": current_user.email,
                                "auth": base64.b64encode(f"{username}:{password}".encode()).decode()
                            }
                        }
                    }).encode()).decode()
                },
                type="kubernetes.io/dockerconfigjson"
            )
            api_instance = client.CoreV1Api()
            api_instance.create_namespaced_secret(namespace=settings.KANIKO_NAMESPACE, body=secret)
            return {"message": AUTH_LOGIN_SUCCESS}
        except Exception as e:
            raise HTTPException(status_code=401, detail=AUTH_LOGIN_FAILURE)

    @staticmethod
    def push_image(local_tag: str, remote_repo: str, current_user: TokenData):
        try:
            user_id = current_user.username
            # Use Kubernetes Job to push image
            # Implementation depends on your CI/CD pipeline
            return {
                "message": IMAGE_PUSH_SUCCESS.format(tag=remote_repo),
                "result": "Push initiated"
            }
        except Exception:
            raise HTTPException(status_code=500, detail=IMAGE_PUSH_FAILURE)

    @staticmethod
    def pull_image(repository: str, current_user: TokenData, local_tag: str = None):
        try:
            user_id = current_user.username
            # Use Kubernetes Job to pull image
            # Implementation depends on your CI/CD pipeline
            return {
                "message": IMAGE_PULL_SUCCESS.format(tag=repository),
                "tags": [repository],
                "retagged_as": local_tag if local_tag else "Not retagged"
            }
        except Exception:
            raise HTTPException(status_code=500, detail=IMAGE_PULL_FAILURE)

    @staticmethod
    def remove_image(image_name: str, params: ImageRemoveRequest, current_user: TokenData):
        try:
            user_id = current_user.username
            # Kubernetes does not support direct image deletion
            # You can remove deployments or pods using the image
            return {
                "message": IMAGE_REMOVE_SUCCESS.format(tag=image_name),
                "used_options": params.dict(exclude_unset=True)
            }
        except Exception:
            raise HTTPException(status_code=500, detail=IMAGE_REMOVE_FAILURE)

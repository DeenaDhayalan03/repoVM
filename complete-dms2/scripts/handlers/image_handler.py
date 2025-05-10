import docker
import re
import os
import tempfile
import git
import shutil
from fastapi import HTTPException, Depends, Query
from typing import Dict, Any, Optional
from scripts.models.image_model import ImageBuildRequest, ImageRemoveRequest, ImageGithubBuildRequest
from scripts.constants.app_constants import *
from scripts.models.jwt_model import TokenData
from fastapi.security import OAuth2PasswordBearer
from scripts.constants.app_configuration import settings
from scripts.utils.jwt_utils import get_current_user_from_token


try:
    client = docker.from_env()
except Exception as e:
    print(e)
    print("Docker is not reachable")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/auth/login")

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

            if build_args.get("fileobj"):
                file_path = build_args.pop("fileobj")
                try:
                    with open(file_path, "rb") as f:
                        build_args["fileobj"] = f
                        image, _ = client.images.build(**build_args)
                except FileNotFoundError:
                    raise HTTPException(status_code=400, detail=f"Dockerfile not found at path: {file_path}")
                except IsADirectoryError:
                    raise HTTPException(status_code=400, detail=f"{file_path} is a directory, not a file.")
            else:
                path = build_args.get("path")
                if path:
                    if not os.path.isdir(path):
                        raise HTTPException(status_code=400, detail=f"{path} is not a valid directory.")
                    build_args["path"] = path
                    image, _ = client.images.build(**build_args)
                else:
                    raise HTTPException(status_code=400, detail="Either 'fileobj' or 'path' must be provided.")

            return {
                "message": IMAGE_BUILD_SUCCESS.format(tag=build_args['tag']),
                "id": image.id,
                "tags": image.tags or ["<none>:<none>"]
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

            dockerfile_dir = os.path.dirname(dockerfile_full_path)
            dockerfile_name = os.path.basename(dockerfile_path)

            image, _ = client.images.build(
                path=dockerfile_dir,
                dockerfile=dockerfile_name,
                tag=data.tag
            )

            shutil.rmtree(temp_dir)

            return {
                "message": IMAGE_BUILD_SUCCESS.format(tag=data.tag),
                "id": image.id,
                "tags": image.tags or ["<none>:<none>"]
            }

        except git.exc.GitCommandError as e:
            raise HTTPException(status_code=400, detail=f"Git error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{IMAGE_BUILD_FAILURE}: {str(e)}")

    @staticmethod
    def list_images(name: str = None, all: bool = False, current_user: TokenData=None):
        try:
            user_id = current_user.username

            kwargs = {}
            if name:
                kwargs["name"] = name
            if all:
                kwargs["all"] = True

            images = client.images.list(**kwargs)

            return {
                "message": IMAGE_LIST_SUCCESS,
                "images": [{"id": img.id, "tags": img.tags} for img in images]
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=IMAGE_LIST_FAILURE)


    @staticmethod
    def dockerhub_login(username: str, password: str, current_user: TokenData):
        try:
            user_id = current_user.username

            client.login(username=username, password=password)
            return {"message": AUTH_LOGIN_SUCCESS}
        except Exception as e:
            raise HTTPException(status_code=401, detail=AUTH_LOGIN_FAILURE)

    @staticmethod
    def push_image(local_tag: str, remote_repo: str, current_user: TokenData):
        try:
            user_id = current_user.username


            image = client.images.get(local_tag)
            image.tag(remote_repo)
            result = client.images.push(remote_repo)

            return {
                "message": IMAGE_PUSH_SUCCESS.format(tag=remote_repo),
                "result": result
            }
        except docker.errors.APIError as e:
            if "unauthorized" in str(e).lower() or "authentication required" in str(e).lower():
                raise HTTPException(status_code=401, detail=UNAUTHORIZED)
            raise HTTPException(status_code=500, detail=IMAGE_PUSH_FAILURE)
        except Exception:
            raise HTTPException(status_code=500, detail=IMAGE_PUSH_FAILURE)

    @staticmethod
    def pull_image(repository: str, current_user: TokenData, local_tag: str = None):
        try:
            user_id = current_user.username

            image = client.images.pull(repository)

            if local_tag:
                image.tag(local_tag)

            return {
                "message": IMAGE_PULL_SUCCESS.format(tag=repository),
                "tags": image.tags,
                "retagged_as": local_tag if local_tag else "Not retagged"
            }

        except docker.errors.APIError as e:
            if "unauthorized" in str(e).lower() or "authentication required" in str(e).lower():
                raise HTTPException(status_code=401, detail=UNAUTHORIZED)
            raise HTTPException(status_code=500, detail=IMAGE_PULL_FAILURE)
        except Exception:
            raise HTTPException(status_code=500, detail=IMAGE_PULL_FAILURE)

    @staticmethod
    def remove_image(image_name: str, params: ImageRemoveRequest, current_user: TokenData):
        try:
            user_id = current_user.username

            opts = params.dict(exclude_unset=True)
            client.images.remove(image=image_name, **opts)

            return {
                "message": IMAGE_REMOVE_SUCCESS.format(tag=image_name),
                "used_options": opts
            }
        except docker.errors.ImageNotFound:
            raise HTTPException(status_code=404, detail=IMAGE_NOT_FOUND)
        except Exception:
            raise HTTPException(status_code=500, detail=IMAGE_REMOVE_FAILURE)
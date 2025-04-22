import docker
import re
import os
import tempfile
from fastapi import HTTPException, Depends
from typing import Dict, Any
from pip._internal.vcs import git
from scripts.models.image_model import ImageBuildRequest, ImageRemoveRequest, ImageGithubBuildRequest
from scripts.constants.app_constants import *
from scripts.constants.app_configuration import settings
from scripts.utils.jwt_utils import get_current_user_from_token


try:
    client = docker.from_env()
except Exception as e:
    print(e)
    print("Docker is not reachable")
oauth2_scheme = None #OAuth2PasswordBearer(tokenUrl=Endpoints.AUTH_LOGIN)

def is_valid_docker_tag(tag: str) -> bool:
    return bool(re.match(r"^[a-z0-9]+([._-]?[a-z0-9]+)*(\/[a-z0-9]+([._-]?[a-z0-9]+)*)*(\:[a-zA-Z0-9_.-]+)?$", tag))

def build_image(data: ImageBuildRequest, token: str = Depends(oauth2_scheme)):
    try:
        build_args = data.dict(exclude_unset=True)

        if not build_args.get("path") and not build_args.get("fileobj"):
            raise HTTPException(status_code=400, detail=INVALID_REQUEST)

        tag = build_args.get("tag")
        if tag:
            if not is_valid_docker_tag(tag):
                raise HTTPException(status_code=400, detail=INVALID_REQUEST)
        else:
            build_args["tag"] = settings.DEFAULT_DOCKER_TAG

        user = get_current_user_from_token(token)
        user_id = user.username

        image, _ = client.images.build(**build_args)

        return {
            "message": IMAGE_BUILD_SUCCESS.format(tag=build_args['tag']),
            "id": image.id,
            "tags": image.tags or ["<none>:<none>"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=IMAGE_BUILD_FAILURE)

def build_image_from_github(data: ImageGithubBuildRequest, token: str = Depends(oauth2_scheme)):
    try:
        temp_dir = tempfile.mkdtemp()
        repo_url = data.github_url
        repo_name = repo_url.split("/")[-1].replace(".git", "")  # Extract repo name
        dockerfile_path = data.dockerfile_path

        git.Repo.clone_from(repo_url, temp_dir)

        dockerfile_full_path = os.path.join(temp_dir, dockerfile_path)
        if not os.path.exists(dockerfile_full_path):
            raise HTTPException(status_code=400, detail=f"Dockerfile not found at {dockerfile_path}")

        build_args = {
            "path": temp_dir,
            "dockerfile": dockerfile_path,
            "tag": data.tag
        }

        user = get_current_user_from_token(token)
        user_id = user.username

        image, _ = client.images.build(**build_args)

        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))
        os.rmdir(temp_dir)

        return {
            "message": IMAGE_BUILD_SUCCESS.format(tag=data.tag),
            "id": image.id,
            "tags": image.tags or ["<none>:<none>"]
        }

    except git.exc.GitCommandError as e:
        raise HTTPException(status_code=400, detail=f"Error cloning GitHub repository: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=IMAGE_BUILD_FAILURE)

def list_images(name: str = None, all: bool = False, filters: Dict[str, Any] = None, token: str = Depends(oauth2_scheme)):
    try:
        user = get_current_user_from_token(token)
        user_id = user.username

        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if all:
            kwargs["all"] = True
        if filters is not None:
            kwargs["filters"] = filters

        images = client.images.list(**kwargs)

        return {
            "message": IMAGE_LIST_SUCCESS,
            "images": [{"id": img.id, "tags": img.tags} for img in images]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=IMAGE_LIST_RETRIEVED)

def dockerhub_login(username: str, password: str, token: str = Depends(oauth2_scheme)):
    try:
        user = get_current_user_from_token(token)
        user_id = user.username

        client.login(username=username, password=password)
        return {"message": AUTH_LOGIN_SUCCESS}
    except Exception as e:
        raise HTTPException(status_code=401, detail=AUTH_LOGIN_FAILURE)

def push_image(local_tag: str, remote_repo: str, token: str = Depends(oauth2_scheme)):
    try:
        user = get_current_user_from_token(token)
        user_id = user.username

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

def pull_image(repository: str, local_tag: str = None, token: str = Depends(oauth2_scheme)):
    try:
        user = get_current_user_from_token(token)
        user_id = user.username

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

def remove_image(image_name: str, params: ImageRemoveRequest, token: str = Depends(oauth2_scheme)):
    try:
        user = get_current_user_from_token(token)
        user_id = user.username

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

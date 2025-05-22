import gzip
import json
import logging
import time
import re
import yaml
import os
from base64 import b64decode
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from functools import lru_cache, wraps
import requests
import traceback
from fastapi import HTTPException
import httpx
import shortuuid
from fastapi import Response
from scripts.services.v1.schemas import (
    GitTargetCreateUpdateSchema,
)

from scripts.constants import STATUS
from scripts.constants.schemas import ExternRequest
from scripts.errors import AuthenticationError
from scripts.utils.docker_util import DockerUtil
from scripts.config import PathConf
from scripts.db.schemas import PluginMetaDBSchema


def timed_lru_cache(seconds: int = 10, maxsize: int = 128):
    def wrapper_cache(func):
        func = lru_cache(maxsize=maxsize)(func)
        func.lifetime = timedelta(seconds=seconds)
        func.expiration = datetime.now(timezone.utc) + func.lifetime

        @wraps(func)
        def wrapped_func(*args, **kwargs):
            if datetime.now(timezone.utc) >= func.expiration:
                logging.debug("Cache Expired")
                func.cache_clear()
                func.expiration = datetime.now(timezone.utc) + func.lifetime

            return func(*args, **kwargs)

        return wrapped_func

    return wrapper_cache


def get_unique_id():
    return shortuuid.uuid()


def hit_external_service(
    api_url, payload=None, request_cookies=None, timeout=60, method="post", params=None, auth=None, headers=None
):
    """
    The hit_external_service function is used to hit external services.

    :param api_url: Call the external service
    :param payload: Pass the data to be sent in the body of a post request
    :param request_cookies: Pass the cookies to the external service
    :param timeout: Set the timeout of the request
    :param method: Determine the type of request to be made
    :param params: Pass the query parameters to the api
    :param auth: Pass the authentication information to the external service
    :param headers: Pass a dictionary of headers to the request
    :return: A dictionary
    """
    try:
        payload_json = ExternRequest(
            url=api_url, timeout=timeout, cookies=request_cookies, params=params, auth=auth, headers=headers
        )
        payload_json = payload_json.model_dump(exclude_none=True)
        if payload:
            payload_json.update(json=payload)
        with httpx.Client() as client:
            for _ in range(3):
                method_type = getattr(client, method)
                resp = method_type(**payload_json)
                logging.debug(f"Resp Code:{resp.status_code}")
                if resp.status_code in STATUS.SUCCESS_CODES:
                    return resp.json()
                elif resp.status_code == 404:
                    logging.error(f"Module not found: {api_url}")
                    raise ModuleNotFoundError
                elif resp.status_code == 401:
                    logging.warning(f"Unauthorized to execute request on {api_url}")
                    raise AuthenticationError
                logging.debug(f"Resp Message:{resp.status_code} \n Cookies: {request_cookies} \n Rest API: {api_url}")
            time.sleep(3)
    except Exception as e:
        logging.error(e)
        raise


def unzip_and_decode_content(data):
    """
    The unzip_and_decode_content function takes in a byte string and returns the decoded JSON object.
        The function first decompresses the data using gzip, then converts it to normal string from base64,
        then decodes it into a json object. If there is an error with any of these steps, an exception will be raised.

    :param data: Pass the data to be decoded
    :return: A dictionary
    """
    try:
        data = gzip.decompress(data)

        # Convert to normal string from base64
        data = b64decode(data)

        try:
            data = data.decode()
        except Exception as e:
            logging.exception(e)
            data = data.decode(encoding="latin1")
        # Convert to json
        data = json.loads(data)
        logging.debug(f"Received keys on decode: {data.keys()}")
        return data
    except Exception as e:
        logging.exception(e)
        raise ValueError("Data issue")


def remove_captcha_cookies(response: Response):
    """
    The remove_captcha_cookies function removes the captcha_cookie and captcha-string cookies from the response.
        This is necessary because if a user fails to solve a CAPTCHA, they will be redirected back to the same page with
        an error message. If we don't remove these cookies, then when they try again, it will still think that they have
        already solved a CAPTCHA.

    :param response: Response: Set the cookies to expire
    :return: The response object with the cookies removed
    """
    response.set_cookie("captcha_cookie", "", expires=0)
    response.set_cookie("captcha-string", "", expires=0)


def fetch_quoted_packages_from_command(command):
    """
    Extracts packages listed in pip install commands from a shell command string.

    This function takes a command string, typically containing a pip install command with package names
    enclosed in single or double quotes, and returns a list of those packages without any duplicates
    or additional flags like "--no-deps".

    :param command: str: The shell command string containing pip install commands and package names.
                        It is expected to be a single string, even if it spans multiple lines.

    :return: list of str: A list of unique package names extracted from the pip install commands in the
                          input command string, excluding any flags like "--no-deps".

    Example:
    >>> command = "pip install 'package1' 'package2' --no-deps"
    >>> fetch_quoted_packages_from_command(command)
    ['package1', 'package2']
    """

    command = command.replace("\n", " ").replace("\\", "")
    pip_blocks = re.findall(r"pip install (['\"][^'\"]+['\"](?:\s+['\"][^'\"]+['\"])*)", command)

    all_packages = []
    for block in pip_blocks:
        packages = re.findall(r"['\"]([^'\"]+)['\"]", block)
        all_packages.extend(packages)

    return [pkg for pkg in all_packages if pkg.strip() != "--no-deps"]


def write_packages_to_file(packages, output_file_path="requirement.txt"):
    """
    Writes a list of package names to a specified output file, ensuring each package is unique and sorted.

    This function takes a list of package names, removes duplicates, sorts them alphabetically, and writes
    each package name on a new line in the specified file. If the file cannot be written, an error message
    is displayed.

    :param packages: list of str: A list of package names to write to the file.
    :param output_file_path: str, optional: The path to the output file where the packages will be saved.
                             Defaults to "requirement.txt".

    :return: None

    Example:
    >>> packages = ["numpy", "pandas", "scipy", "numpy"]
    >>> write_packages_to_file(packages, "requirements.txt")
    Packages written to requirements.txt
    """
    try:
        unique_packages = set(packages)
        with open(output_file_path, "w") as output_file:
            for package in sorted(unique_packages):
                output_file.write(f"{package}\n")
        logging.info(f"Packages written to {output_file_path}")
    except Exception as e:
        logging.info(f"Error writing to {output_file_path}: {e}")


def get_new_image_tag(yaml_documents, base_tag="azrilensprod.azurecr.io/ftdm/base-images/python"):
    """
    Generates a new image tag by incrementing the highest existing version number found in the provided YAML documents.

    This function scans through the YAML documents to find the highest version number of an image that matches the specified
    base tag. It then increments this version by 1 to create a new unique image tag. If no versioned image is found, it
    defaults to version 1.

    :param yaml_documents: list of dict: Parsed YAML documents containing potential image tags for inspection.
    :param base_tag: str, optional: The base path of the image to filter and identify the relevant images.
                                Defaults to "azrilensprod.azurecr.io/ftdm/base-images/python".

    :return: str: A new image tag in the format "base_tag:v.<version>", where <version> is the incremented version.
    """
    version = 1
    for doc in yaml_documents:
        image_tag = doc.get("image") or next(
            (
                template["container"]["image"]
                for template in doc.get("deploymentSpec", {}).get("executors", {}).values()
                if "container" in template and "image" in template["container"]
            ),
            None,
        )

        if image_tag and image_tag.startswith(base_tag):
            match = re.search(r":v\.(\d+)$", image_tag)
            if match:
                version = max(version, int(match.group(1)) + 1)

    return f"{base_tag}:v.{version}"


def build_docker_image(base_image, image_tag, folder_path, requirements_path="kubeflow_requirements.txt"):
    """
    Builds a Docker image from a specified base image, adding dependencies listed in a requirements file.

    This function generates a Dockerfile that starts with the specified base image, copies the requirements file
    to the image, and installs the dependencies. It then builds the Docker image with the given tag.

    :param base_image: str: The base image to use in the Dockerfile (e.g., "python:3.8").
    :param image_tag: str: The tag to assign to the newly built Docker image (e.g., "my_image:latest").
    :param folder_path: str: The path to the folder where the Dockerfile should be created.
    :param requirements_path: str, optional: Path to the requirements file listing dependencies (default is "requirement.txt").

    :return: None
    """
    docker_util = DockerUtil()
    dockerfile_content = f"""
    FROM {base_image}
    COPY {requirements_path} /app/{requirements_path}
    RUN pip install -r /app/{requirements_path}
    """
    parent_folder = os.path.dirname(folder_path)
    os.makedirs(parent_folder, exist_ok=True)
    dockerfile_path = os.path.join(parent_folder, "Dockerfile")
    with open(dockerfile_path, "w") as dockerfile:
        dockerfile.write(dockerfile_content)

    try:
        docker_util.build_docker_image_for_kubeflow(parent_folder, image_tag)
        logging.info(f"Docker image {image_tag} built successfully.")
    except Exception as e:
        logging.error(f"Error building Docker image: {e}")


def update_yaml_image(yaml_file_path):
    try:
        with open(yaml_file_path) as file:
            yaml_documents = list(yaml.safe_load_all(file))

        for doc in yaml_documents:
            if "image" in doc:
                doc["image"] = "new_image_name"
            for template in doc.get("deploymentSpec", {}).get("executors", {}).values():
                if "container" in template and "image" in template["container"]:
                    template["container"]["image"] = "new_image_tag"
        with open(yaml_file_path, "w") as file:
            yaml.dump_all(yaml_documents, file)
        logging.info(f"The YAML file '{yaml_file_path}' has been updated with the new image name.")
    except Exception as e:
        logging.error(f"Error updating the YAML file: {e}")


def extract_packages_and_image_from_yaml(
    yaml_file_path, output_file_path, name, base_tag="azrilensprod.azurecr.io/ftdm/base-images/python"
):
    """
    Extracts packages and image details from a YAML file, writes packages to a requirements file,
    builds a new Docker image, and updates the YAML file with the new image tag.

    This function parses a YAML file to find any specified container images and dependencies (within shell commands),
    compiles the dependencies into a requirements file, builds a new Docker image, and updates the YAML file
    with the generated image tag.

    :param yaml_file_path: str: Path to the YAML file containing deployment configurations.
    :param output_file_path: str, optional: Path for saving the requirements file with extracted packages (default is "requirement.txt").
    :param base_tag: str, optional: Base tag for the Docker image (default is a specific repository base image).

    :return: None
    """
    try:
        yaml_documents = load_yaml_documents(yaml_file_path)
        images, all_packages = extract_images_and_packages(yaml_documents)

        write_packages_to_file(all_packages, output_file_path)

        base_image = images.pop() if images else "python:3.9-slim"
        new_image_tag = get_new_image_tag(yaml_documents, base_tag)

        build_docker_image(base_image, new_image_tag, output_file_path)
        update_yaml_image(yaml_file_path)
        strip_single_quotes_from_yaml(yaml_file_path)
        copy_contents_to_local_path(yaml_file_path, name)
        convert_to_tar_file(new_image_tag, name)
    except Exception as e:
        logging.error(f"Error processing the YAML file: {e}")


def load_yaml_documents(yaml_file_path):
    with open(yaml_file_path) as yaml_file:
        return list(yaml.safe_load_all(yaml_file))


def extract_images_and_packages(yaml_documents):
    images = set()
    all_packages = []
    for yaml_content in yaml_documents:
        extract_images(yaml_content, images)
        extract_packages(yaml_content, all_packages)

    return images, all_packages


def extract_images(yaml_content, images):
    if "image" in yaml_content:
        images.add(yaml_content["image"])
    for template in yaml_content.get("deploymentSpec", {}).get("executors", {}).values():
        if "container" in template and "image" in template["container"]:
            images.add(template["container"]["image"])


def extract_packages(yaml_content, all_packages):
    for template in yaml_content.get("deploymentSpec", {}).get("executors", {}).values():
        if "container" in template and "command" in template["container"]:
            command = " ".join(template["container"]["command"])
            if re.match(r"sh\s+-c", command):
                packages = fetch_quoted_packages_from_command(command)
                all_packages.extend(packages)


def strip_single_quotes_from_yaml(yaml_file_path):
    """
    Removes all single-quoted strings from a YAML file and saves the updated content.

    This function reads the content of a specified YAML file, removes any text enclosed in single quotes,
    and overwrites the file with the updated content.

    :param yaml_file_path: str: Path to the YAML file to be modified.

    :return: None
    """
    try:
        with open(yaml_file_path) as file:
            yaml_content = file.read()

        updated_yaml_content = re.sub(r"'[^']*'", "", yaml_content)

        with open(yaml_file_path, "w") as file:
            file.write(updated_yaml_content)

        logging.info(f"The YAML file '{yaml_file_path}' has been updated.")
    except Exception as e:
        logging.error(f"Error updating the YAML file: {e}")


def copy_contents_to_local_path(yaml_file_path, name: PluginMetaDBSchema):
    """
    Copies kubeflow_requirements.txt and pipeline.yml to PathConf.LOCAL_IMAGE_PATH/plugin_id folder.

    :param folder_path: str: Path to the folder containing the files to be copied.
    :param plugin_id: str: The plugin ID to be used as the folder name in the destination path.

    :return: None
    """
    try:
        os.makedirs(os.path.join(PathConf.LOCAL_IMAGE_PATH, name), exist_ok=True)
        shutil.copyfile(yaml_file_path, os.path.join(PathConf.LOCAL_IMAGE_PATH, name, "pipeline.yml"))
    except Exception as e:
        logging.error(f"Error copying files: {e}")


def convert_to_tar_file(new_image_tag, name):
    docker_util = DockerUtil()
    byte_stream = docker_util.save_image(new_image_tag)
    tar_file_path = os.path.join(PathConf.LOCAL_IMAGE_PATH, name, "kubeflow.tar")

    with open(tar_file_path, "wb") as f:
        for chunk in byte_stream:
            f.write(chunk)

    logging.info(f"Docker image saved to {tar_file_path}")

    # Call container_blob_signing with the tar file path and the local image directory
    local_image_dir = os.path.dirname(tar_file_path)
    docker_util.container_blob_signing(tar_file_path, local_image_dir)

    # Define the paths for the other files
    pipeline_path = os.path.join(PathConf.LOCAL_IMAGE_PATH, name, "pipeline.yml")
    signature_path = os.path.join(local_image_dir, "signature")

    # Ensure all files exist before zipping
    if not all(os.path.exists(path) for path in [pipeline_path, signature_path, tar_file_path]):
        logging.error("One or more files to be zipped are missing.")
        return

    # Create a zip archive containing all the files
    source_dir = Path(local_image_dir)
    destination_zip = Path(f"{local_image_dir}.zip")
    shutil.make_archive(
        str(destination_zip.with_suffix("")),
        "zip",
        str(source_dir.parent),
        source_dir.name,
    )
    shutil.rmtree(local_image_dir)

    logging.info(f"Image and signature zipped as: {destination_zip}")


def fetch_projects(target: GitTargetCreateUpdateSchema, gitlab_token):
    """
    Fetch and list all projects under a specified GitLab group.
    Verifies GitLab token, validates username, and fetches the projects.
    """
    try:

        # Verify the GitLab token by making a test request to GitLab API
        token_response = requests.get(
            target.git_common_url,
            headers={"PRIVATE-TOKEN": gitlab_token},
        )
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail="Authentication failed. Please verify your credentials and try again.",
            )

        # Validate the username by checking its existence on GitLab
        username_response = requests.get(
            target.git_common_url,
            headers={"PRIVATE-TOKEN": gitlab_token},
            params={"username": target.username},
        )
        if username_response.status_code != 200 or not any(
            user["username"] == target.username for user in username_response.json()
        ):
            raise HTTPException(
                status_code=404,
                detail=f"Username '{target.username}' not found or is invalid.",
            )
        # Fetch the group ID by searching for the group path
        group_response = requests.get(
            target.git_common_url,
            headers={"PRIVATE-TOKEN": gitlab_token},
            params={"search": target.git_common_url.split("/")[-1]},
        )
        if group_response.status_code != 200:
            raise HTTPException(
                status_code=group_response.status_code, detail=f"Failed to fetch group ID: {group_response.text}"
            )

        # Find the exact group by matching the full path
        group_id = next(
            (
                group_data["id"]
                for group_data in group_response.json()
                if group_data["full_path"] == target.git_common_url
            ),
            None,
        )
        if not group_id:
            raise HTTPException(status_code=404, detail=f"Group '{target.git_common_url}' not found.")

        # Fetch all projects under the specified group using pagination
        projects = []
        page = 1
        while True:
            project_response = requests.get(
                # f"{GITLAB_URL}/groups/{group_id}/projects",
                target.git_common_url,
                headers={"PRIVATE-TOKEN": gitlab_token},
                params={"page": page, "per_page": 100},
            )
            if project_response.status_code != 200:
                raise HTTPException(
                    status_code=project_response.status_code, detail=f"Error fetching projects: {project_response.text}"
                )

            page_data = project_response.json()
            if not page_data:
                break  # Exit when no more projects are found

            projects.extend(page_data)
            page += 1

        # Return a success response with project details
        return {
            "message": "The credentials have been verified and authenticated.",
            "status": "success",
            "total_projects": len(projects),
            "group_path": target.git_common_url,
            "username": target.username,
            "projects": projects,  # Include all project details in the response
        }
    except Exception as e:
        error_message = f"Unexpected error: {e}"
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_message)

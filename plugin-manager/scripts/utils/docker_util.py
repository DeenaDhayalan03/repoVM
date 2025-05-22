import json
import logging
import os
import shutil
from pathlib import Path
import subprocess
import docker
import docker.errors
from docker.errors import BuildError
from jinja2 import Environment, FileSystemLoader

from scripts.config import (
    AzureCredentials,
    ContainerSigningSettings,
    Services,
    VulnerabilityScanner,
)
from scripts.db.schemas import VulnerabilityReportSchema
from scripts.db.schemas import PluginMetaDBSchema
from scripts.db.mongo.plugins.plugin_meta import PluginMeta


class DockerUtil:
    def __init__(self):
        self.docker_client = docker.DockerClient(base_url=Services.DOCKER_HOST)
        self.plugin_db_conn = PluginMeta()

    def build_docker_image(self, files_path: str, image_tag: str, container_registry_url: str, build_args: dict = None):
        try:
            image_uri = f"{container_registry_url}/{image_tag}"
            logging.debug("In Build Docker image")
            logging.info(f"files_path {files_path}")
            build_output = self.docker_client.images.build(
                path=files_path, tag=image_uri, buildargs=build_args, network_mode="host"
            )
            for line in build_output:
                logging.info(f"{line}")
            logging.debug("Built Docker image")
            shutil.rmtree(files_path)
        except BuildError as build_error:
            logging.exception(build_error)
            raise build_error
        except Exception as e:
            # Windows file deletion exception pass
            logging.exception(e)
            raise

    def build_docker_image_for_kubeflow(self, files_path: str, image_tag: str, build_args: dict = None):
        try:
            image_uri = f"{image_tag}"
            logging.debug("In Build Docker image")
            logging.info(f"files_path {files_path}")
            build_output = self.docker_client.images.build(
                path=files_path, tag=image_uri, buildargs=build_args, network_mode="host"
            )
            for line in build_output:
                logging.info(f"{line}")
            logging.debug("Built Docker image")
            # shutil.rmtree(files_path)
        except BuildError as build_error:
            logging.exception(build_error)
            raise build_error
        except Exception as e:
            # Windows file deletion exception pass
            logging.exception(e)
            raise

    def push_docker_image(self, image_tag: str, container_registry_credentials: dict, container_registry_url: str):
        try:
            logging.debug("Pushing Docker Image")
            self.docker_client.login(
                username=container_registry_credentials["username"],
                password=container_registry_credentials["password"],
                registry=container_registry_url,
            )
            image_full_path = f"{container_registry_url}/{image_tag}"
            push_output = self.docker_client.images.push(repository=image_full_path, stream=True, decode=True)
            for line in push_output:
                if "status" in line:
                    logging.info(f"status is {line}")

            logging.info(f"Docker Image Pushed {image_full_path}")
            return image_full_path
        except Exception as e:
            logging.exception(e)
            raise

    def load_docker_image(
        self, docker_tar_file_path, new_image_name, container_registry_url, container_registry_credentials
    ):
        try:
            self.docker_client.login(
                username=container_registry_credentials["username"],
                password=container_registry_credentials["password"],
                registry=container_registry_url,
            )
            with open(docker_tar_file_path, "rb") as tar_file:
                images = self.docker_client.images.load(tar_file.read())
            image = images[0]
            image.tag(f"{container_registry_url}/{new_image_name}")
            return image
        except Exception as e:
            logging.exception(f"Unexpected: {e}")

    @staticmethod
    def dockerfile_generator(path: Path, config: dict, docs: bool = False):
        env = Environment(loader=FileSystemLoader("."), autoescape=True)
        if docs:
            template = env.get_template("templates/Dockerfile-template-v2")
        else:
            template = env.get_template("templates/Dockerfile-template")
        dockerfile_variables = {
            "backend_base_image": config.get("backend_base_image", "python:3.10.10-slim"),
            "frontend_base_image": config.get("frontend_base_image", "node:14.16.1"),
        }
        dockerfile = template.render(dockerfile_variables)
        with open(path / "Dockerfile", "w") as f:
            f.write(dockerfile)

    def scan_image(self, image: str, plugin_data: PluginMetaDBSchema = None, folder_path: str = "/"):
        try:
            root_path = "/"
            temp_path = os.path.join(root_path, "tmp", "output")

            if plugin_data is not None:
                self.plugin_db_conn.update_plugin(plugin_data.plugin_id, {"status": "Vulnerability Scan Started"})

            logging.info("Scanning image for vulnerabilities")
            volumes = {
                "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
                f"{VulnerabilityScanner.VULNERABILITY_FOLDER_PATH}{folder_path}": {
                    "bind": temp_path,
                    "mode": "rw",
                },
            }
            self.docker_client.containers.run(
                "aquasec/trivy:0.44.1",
                f"image --ignore-unfixed --timeout 10m --cache-dir /tmp/trivy/ --scanners vuln --severity {VulnerabilityScanner.VULNERABILITY_SCAN_LEVEL} --format json --output /tmp/output/scan-output.json  {image}  --username {AzureCredentials.azure_registry_username} --password {AzureCredentials.azure_registry_password}",
                volumes=volumes,
                detach=False,
                network_mode="host",
                group_add=[2000],
                remove=True,
            )

            logging.info("Image scan complete")
            if plugin_data is not None:
                self.plugin_db_conn.update_plugin(
                    plugin_data.plugin_id, {"status": "Scanning in progress"}, version=plugin_data.version
                )
            return True
        except Exception as e:
            logging.exception(e)
            if plugin_data is not None:
                self.plugin_db_conn.update_plugin(
                    plugin_data.plugin_id, {"status": "Vulnerability Scan Failed"}, version=plugin_data.version
                )
        return False

    def scan_report_parser(self, folder_path: str = ""):
        try:
            logging.info("Generating vulnerability scan report")
            with open(f"{VulnerabilityScanner.REPORT_FOLDER_PATH}{folder_path}/scan-output.json") as f:
                data = json.load(f)
            # os.remove(f"{VulnerabilityScanner.REPORT_FOLDER_PATH}{folder_path}/scan-output.json")
            results = data.get("Results", [])
            vulnerabilities = self.get_vulnerabilites_from_report(results)
            return {"vulnerabilities": vulnerabilities}
        except Exception as e:
            logging.exception(e)
            return {"vulnerabilities": []}

    def get_vulnerabilites_from_report(self, data: list):
        vulnerabilities = []
        for target in data:
            if target.get("Vulnerabilities") and target.get("Type") == "python-pkg":
                vulnerabilities.extend(
                    VulnerabilityReportSchema(
                        Package=_vulnerability.get("PkgName", ""),
                        PackageType=target.get("Type", ""),
                        Path=_vulnerability.get("PkgPath", None),
                        InstalledVersion=_vulnerability.get("InstalledVersion", ""),
                        FixedVersion=_vulnerability.get("FixedVersion", None),
                        Severity=_vulnerability.get("Severity", None),
                        Description=_vulnerability.get("Description", ""),
                    ).model_dump()
                    for _vulnerability in target.get("Vulnerabilities")
                )
        return vulnerabilities

    def clamav_antivirus_scan(self, folder_path: str = "/", plugin_name: str = "", plugin_id: str = ""):
        try:
            logging.info("Scanning file for viruses")
            report_path = f"{VulnerabilityScanner.ANTIVIRUS_FOLDER_PATH}/{plugin_name}/{plugin_id}"
            logging.info(f"report_path {report_path}")
            volumes = {
                folder_path: {"bind": "/scandir", "mode": "rw"},
                report_path: {
                    "bind": "/output/",
                    "mode": "rw",
                },
            }
            self.docker_client.containers.run(
                "clamav/clamav:1.2",
                "clamscan /scandir -r -l /output/scan-output.txt",
                userns_mode="host",
                group_add=[2000],
                volumes=volumes,
                detach=False,
                remove=True,
            )
            return True
        except Exception as e:
            logging.exception(e)
            return False

    def antivirus_scan_parser(self, output: str):
        output_lines = output.split("\n")
        parsed_data = {}
        for line in output_lines:
            if line != "" and "------" not in line:
                key, value = map(str.strip, line.split(": ", 1))
                parsed_data[key] = value
        return parsed_data

    def antivirus_report(self, folder_path: str = ""):
        try:
            logging.info("Generating antivirus scan report")
            with open(f"{VulnerabilityScanner.ANTIVIRUS_REPORT_FOLDER_PATH}{folder_path}/scan-output.txt") as f:
                data = f.read()
            # os.remove(f"{VulnerabilityScanner.ANTIVIRUS_REPORT_FOLDER_PATH}{folder_path}/scan-output.txt")
            parsed_data = self.antivirus_scan_parser(data) or {}
            return True, parsed_data
        except Exception as e:
            logging.exception(e)
            return False, {}

    def container_signing(self, image: str):
        try:
            if not ContainerSigningSettings.SIGNING_ENABLED:
                return True

            image_info = self.docker_client.images.get(image).attrs
            repo_digests = image_info.get("RepoDigests", [])

            if not repo_digests:
                image_digest = image
            else:
                # Find the digest that corresponds to the provided image tag
                image_digest = None
                for digest in repo_digests:
                    if image in digest:
                        image_digest = digest
                        break

                if not image_digest:
                    image_digest = image

            logging.debug(f"Image Digest {image_digest}")
            os.system(
                f"cosign sign --key={ContainerSigningSettings.SIGNING_KEY_PATH} {image_digest} "
                f"--registry-username={AzureCredentials.azure_registry_username} "
                f"--registry-password={AzureCredentials.azure_registry_password} "
                f"--allow-insecure-registry={ContainerSigningSettings.ALLOW_INSECURE_REGISTRY} "
                f"--allow-http-registry={ContainerSigningSettings.ALLOW_HTTP_REGISTRY} -y"
            )
        except Exception as e:
            logging.exception(e)
            return False
        return True

    def container_blob_signing(self, tar_image, local_image_dir):
        try:
            if not ContainerSigningSettings.SIGNING_ENABLED:
                return True
            os.system(
                f"cosign --key={ContainerSigningSettings.SIGNING_KEY_PATH} --output-signature={local_image_dir}/signature sign-blob {tar_image} -y"
            )
            return True
        except Exception as e:
            logging.exception(e)
            return False

    def container_blob_verifying(self, file_path, kubeflow=False):
        logging.info(f"Starting blob verification for file path: {file_path}")
        try:
            # Check if signing is enabled
            if not ContainerSigningSettings.SIGNING_ENABLED:
                logging.info("Container signing is not enabled. Skipping verification.")
                return True
            image_file_path = f"{file_path}/kubeflow.tar" if kubeflow else f"{file_path}/plugin.tar"
            command = [
                "cosign",
                "verify-blob",
                f"--key={ContainerSigningSettings.VERIFY_PUB_PATH}",
                "--offline=true",
                "--private-infrastructure=true",
                f"--signature={file_path}/signature",
                f"{image_file_path}",
            ]

            logging.info(f"Running command: {' '.join(command)}")
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            logging.info(f"Command stdout: {result.stdout}")
            logging.info(f"Command stderr: {result.stderr}")

            if result.returncode == 0:
                logging.info("Verification succeeded")
                return True
            else:
                logging.error("Verification failed with return code")
                return False

        except Exception as e:
            logging.exception(f"Exception occurred during verification: {e}")
            return False

    def save_image(self, image_tag):
        image = self.docker_client.images.get(image_tag)
        return image.save(named=True)

    def pull_image(self, image_tag, container_registry_url, container_registry_credentials):
        self.docker_client.login(
            username=container_registry_credentials["username"],
            password=container_registry_credentials["password"],
            registry=container_registry_url,
        )
        self.docker_client.images.pull(image_tag)

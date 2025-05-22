import os
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock, mock_open
from scripts.utils.docker_util import DockerUtil

builtins_open = "builtins.open"
docker_container_run = "docker.models.containers.ContainerCollection.run"


@pytest.fixture
def docker_util():
    return DockerUtil()


@pytest.fixture
def docker_credentials():
    return {"username": "user", "password": os.getenv("DOCKER_PASSWORD", "default_pass")}


def test_build_docker_image_success(docker_util):
    with patch("docker.models.images.ImageCollection.build", return_value=[{"stream": "Successfully built"}]):
        with patch("shutil.rmtree"):
            result = docker_util.build_docker_image("test_path", "test_image", "test_registry")
    assert result is None  # Assuming the function does not return anything


def test_build_docker_image_failure(docker_util):
    with patch("docker.models.images.ImageCollection.build", side_effect=Exception("Build error")):
        with pytest.raises(Exception, match="Build error"):
            docker_util.build_docker_image("test_path", "test_image", "test_registry")


def test_push_docker_image_success(docker_util, docker_credentials):
    with patch("docker.models.images.ImageCollection.push", return_value=[{"status": "Pushed"}]):
        with patch("docker.DockerClient.login"):
            result = docker_util.push_docker_image("test_image", docker_credentials, "test_registry")
    assert result == "test_registry/test_image"


def test_push_docker_image_failure(docker_util, docker_credentials):
    with patch("docker.models.images.ImageCollection.push", side_effect=Exception("Push error")):
        with patch("docker.DockerClient.login"):
            with pytest.raises(Exception, match="Push error"):
                docker_util.push_docker_image("test_image", docker_credentials, "test_registry")


def test_dockerfile_generator_with_docs(docker_util):
    with patch(builtins_open, mock_open()):
        with patch("jinja2.Environment.get_template", return_value=MagicMock(render=lambda x: "Dockerfile content")):
            result = docker_util.dockerfile_generator(Path("."), {}, docs=True)
    assert result is None


def test_dockerfile_generator_without_docs(docker_util):
    with patch(builtins_open, mock_open()):
        with patch("jinja2.Environment.get_template", return_value=MagicMock(render=lambda x: "Dockerfile content")):
            result = docker_util.dockerfile_generator(Path("."), {}, docs=False)
    assert result is None


def test_scan_image_success(docker_util):
    with patch(docker_container_run):
        result = docker_util.scan_image("test_image")
    assert result is True


def test_scan_image_failure(docker_util):
    with patch(docker_container_run, side_effect=Exception("Scan error")):
        result = docker_util.scan_image("test_image")
    assert result is False


def test_scan_report_parser_success(docker_util):
    with patch(builtins_open, mock_open(read_data='{"Results": []}')):
        result = docker_util.scan_report_parser()
    assert result == {"vulnerabilities": []}


def test_scan_report_parser_failure(docker_util):
    with patch(builtins_open, side_effect=Exception("File error")):
        result = docker_util.scan_report_parser()
    assert result == {"vulnerabilities": []}


def test_clamav_antivirus_scan_success(docker_util):
    with patch(docker_container_run):
        result = docker_util.clamav_antivirus_scan()
    assert result is True


def test_clamav_antivirus_scan_failure(docker_util):
    with patch(docker_container_run, side_effect=Exception("Scan error")):
        result = docker_util.clamav_antivirus_scan()
    assert result is False


def test_antivirus_report_success(docker_util):
    with patch(builtins_open, mock_open(read_data="Scan output")):
        with patch.object(docker_util, "antivirus_scan_parser", return_value={"key": "value"}):
            result, data = docker_util.antivirus_report()
    assert result is True
    assert data == {"key": "value"}


def test_antivirus_report_failure(docker_util):
    with patch(builtins_open, side_effect=Exception("File error")):
        result, data = docker_util.antivirus_report()
    assert result is False
    assert data == {}


def test_container_signing_success(docker_util):
    with patch("docker.models.images.ImageCollection.get", return_value=MagicMock(attrs={"RepoDigests": ["digest"]})):
        with patch("os.system", return_value=0):
            result = docker_util.container_signing("test_image")
    assert result is True


def test_container_signing_failure(docker_util):
    with patch("docker.models.images.ImageCollection.get", side_effect=Exception("Signing error")):
        result = docker_util.container_signing("test_image")
    assert result is False

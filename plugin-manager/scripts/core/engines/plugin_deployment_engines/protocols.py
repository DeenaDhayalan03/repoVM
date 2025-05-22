import ast
import json
import logging
import os
import shutil

import httpx
from ut_security_util import create_token

from scripts.config import ExternalServices, PathConf, Secrets

from . import DeploymentEngineMixin


class DeploymentEngine(DeploymentEngineMixin):
    def __init__(self, project_id: str):
        self.project_id = project_id

    @staticmethod
    def read_file(file_full_path):
        file_content = None
        try:
            with open(file_full_path) as file:
                file_content = file.read()
        except FileNotFoundError as e:
            logging.exception(f"File not found {e}")
        return file_content

    @staticmethod
    def url_request(user_details, data, call_type):
        resp = None
        try:
            httpx_timeout = httpx.Timeout(30, read=None, write=None)
            cookies = {
                "login-token": create_token(
                    project_id=user_details.project_id,
                    user_id=user_details.user_id,
                    ip=user_details.ip_address,
                    token=Secrets.token,
                )
            }
            with httpx.Client() as client:
                if call_type == "create":
                    resp = client.post(
                        url=f"{ExternalServices.DCP_URL}/ilens_config/create_plugin_protocol",
                        cookies=cookies,
                        headers={"project_id": user_details.project_id},
                        json=data,
                        timeout=httpx_timeout,
                    )
                else:
                    resp = client.post(
                        url=f"{ExternalServices.DCP_URL}/ilens_config/protocol_check",
                        cookies=cookies,
                        headers={"project_id": user_details.project_id},
                        json=data,
                        timeout=httpx_timeout,
                    )
                logging.info(f"Resp Code:{resp.status_code}")
        except Exception as e:
            logging.exception(f"Exception occurred while connecting to server {e}")
        return resp

    @staticmethod
    def error_message(file_name, line_no, msg, offset=None):
        """
        Creating the error message
        """
        if not offset:
            msg = f"{file_name}:{line_no} {msg}"
        else:
            msg = f"{file_name}:{line_no}:{offset} {msg}"
        return msg

    def formatting_check(self, file_full_path, file_content, error_list):
        """
        Checking for formatting and getting the class and function names
        """
        try:
            class_name = None
            function_names = ["connect", "disconnect", "perform_task"]
            file_name = file_full_path.split("\\")[-1]
            if not file_content:
                error_list["errors"].append(self.error_message(file_name, 0, "File Not Found"))
                return error_list
            try:
                tree = ast.parse(file_content)
            except SyntaxError as e:
                error_list["syntax_errors"].append(self.error_message(file_name, e.lineno, e.text.strip(), e.offset))
                return error_list
            for nodes in ast.walk(tree):
                if isinstance(nodes, ast.ClassDef):
                    class_name = nodes.name
                if isinstance(nodes, ast.FunctionDef) and nodes.name in function_names:
                    function_names.remove(nodes.name)
            if function_names:
                error_list["errors"].append(
                    self.error_message(file_name, 0, f"Function names are not present {function_names}")
                )
                return error_list
            if not class_name:
                error_list["errors"].append(f"{file_name} doesn't contain any class names")
            error_list["class_name"] = class_name
            return error_list
        except Exception as e:
            logging.exception(f"Exception occurred while checking Formatting: {e}")
        return error_list

    def get_class_name(self, file_path):
        """
        Checking for getting the class name
        """
        class_name = None
        try:
            file_content = self.read_file(file_path)
            if not file_content:
                return None
            tree = ast.parse(file_content)
            for nodes in ast.walk(tree):
                if isinstance(nodes, ast.ClassDef):
                    class_name = nodes.name
            return class_name
        except Exception as e:
            logging.exception(f"Exception occurred while checking Formatting: {e}")
        return class_name

    def protocol_validate_utils(self, file_full_path, file_contents):
        """
        check if the protocol.py file is valid
        """
        error_list = {"syntax_errors": [], "errors": []}
        try:
            error_list = self.formatting_check(file_full_path, file_contents, error_list)
        except Exception as e:
            logging.exception(f"Exception occurred while validating protocol: {e}")
        return error_list

    def dcp_url_request(self, plugin_data, user_details, data, files, files_path):
        try:
            response = self.url_request(user_details, data, "create")
            if response.status_code in (200, 201, 204) and response.json()["status"]:
                protocol_folder = os.path.join(
                    PathConf.PROTOCOL_PLUGIN_COMMON_PATH,
                    os.path.join(str(user_details.project_id), data["protocol_name"]),
                )
                if not os.path.exists(protocol_folder):
                    os.makedirs(protocol_folder, exist_ok=True)
                for file in files:
                    file_full_path = os.path.join(files_path, file)
                    if file.endswith(".py"):
                        shutil.copyfile(
                            file_full_path,
                            os.path.join(protocol_folder, data["protocol_name"] + ".py"),
                        )
                    else:
                        shutil.copyfile(file_full_path, os.path.join(protocol_folder, file))
            else:
                plugin_data.errors.append(f"Server response {response.status_code}")
        except AttributeError:
            plugin_data.errors.append("No response from the server")
        except Exception as e:
            logging.exception(f"Exception occurred while dcp url request: {e}")

    def get_protocol(self, plugin_id, plugin_data, files_path, user_details):
        response = {"message": ""}
        try:
            try:
                files = [f for f in os.listdir(files_path) if os.path.isfile(os.path.join(files_path, f))]
            except (FileNotFoundError, TypeError) as e:
                logging.error(f"Error occurred while getting files from location: {e}")
                plugin_data.errors.append(str(e))
                return response
            if len(files) != 3:
                response["message"] = "Files not found"
            class_name = None
            for file in files:
                if file.endswith(".py"):
                    python_path = os.path.join(files_path, file)
                    class_name = self.get_class_name(python_path)
                    if not class_name:
                        response["message"] = "Protocol File issue"
            if class_name:
                json_name = [file for file in files if file.endswith(".json")]
                with open(os.path.join(files_path, json_name[0])) as json_file:
                    file_contents = json.load(json_file)
                    data = {
                        "plugin_id": plugin_id,
                        "fields": file_contents,
                        "protocol_name": class_name,
                    }
                    self.dcp_url_request(plugin_data, user_details, data, files, files_path)
            response["message"] = "success"
            return response
        except Exception as e:
            logging.exception(f"Exception occurred while getting protocol: {e}")
        logging.exception(f"Exception occurred while getting protocol: {response}")

    def check_file_contents(  # NOSONAR
        self,
        file_name,
        file_contents,
        data,
        _is_python_file_present,
        _is_json_file_present,
        _is_txt_file_present,
    ):
        """
        Checking the file contents
        """
        try:
            if file_name.endswith(".py"):
                _is_python_file_present = True
                response = self.protocol_validate_utils(file_name, file_contents)
                if "errors" in response and response["errors"]:
                    data["errors"].append(response["errors"])
                if "syntax_errors" in response and response["syntax_errors"]:
                    data["syntax_errors"].append(response["syntax_errors"][0])
                if "class_name" in response:
                    data["class_name"] = response["class_name"]
            if file_name.endswith(".json"):
                _is_json_file_present = True
                try:
                    file_contents = json.loads(file_contents)
                    if not file_contents:
                        data["errors"].append(f"{file_name}: Json File is empty")
                except json.JSONDecodeError:
                    data["syntax_errors"].append(f"{file_name}: Syntax Error in Json File")
            if file_name.endswith(".txt"):
                _is_txt_file_present = True
                if not len(file_contents):
                    data["errors"].append(f"{file_name}: Requirements File cannot be empty")
            return (
                data,
                _is_python_file_present,
                _is_json_file_present,
                _is_txt_file_present,
            )
        except Exception as e:
            logging.exception(f"Exception occurred while checking file contents {e}")
        return data

    def validate_protocol(self, user_details, files):  # NOSONAR
        """
        Check if the files are valid
        """
        data = {"syntax_errors": [], "errors": []}
        _is_python_file_present = False
        _is_json_file_present = False
        _is_txt_file_present = False
        try:
            class_name = None
            for file in files:
                file_name = file.filename
                file_contents = file.file.read().decode("utf-8")
                (
                    data,
                    _is_python_file_present,
                    _is_json_file_present,
                    _is_txt_file_present,
                ) = self.check_file_contents(
                    file_name,
                    file_contents,
                    data,
                    _is_python_file_present,
                    _is_json_file_present,
                    _is_txt_file_present,
                )
                if "class_name" in data:
                    class_name = data["class_name"]
                    data.pop("class_name")
            if not _is_python_file_present:
                data["errors"].append("Protocol File is required")
            if not _is_json_file_present:
                data["errors"].append("Input Json is required")
            if not _is_txt_file_present:
                data["errors"].append("Requirements file is required")
            if not data["errors"] and not data["syntax_errors"]:
                data.pop("syntax_errors")
                if not class_name:
                    data["errors"].append("Class name in protocol file is required")
                else:
                    request_data = {"name": class_name}
                    url_response = self.url_request(user_details, request_data, "validate")
                    if url_response.status_code in (200, 201, 204) and url_response.json()["status"] == "success":
                        data = {
                            "validation": True,
                            "additional_fields": [{"label": "Protocol Name", "value": class_name}],
                            "validation_message": "Validation successful",
                        }
                    elif url_response.status_code in [301]:
                        logging.exception("Endpoint not found")
                        data["errors"] = ["Try again"]
                    else:
                        data["errors"] = [f"{class_name}: Protocol already exists"]
            return data
        except Exception as e:
            logging.exception(f"Exception occurred while validating the file {e}")
        return data

    def register(self, plugin_data, user_details):
        plugin_meta = plugin_data.model_dump()
        if plugin_meta["plugin_type"].lower() == "protocols":
            self.get_protocol(
                plugin_meta["plugin_id"],
                plugin_data,
                plugin_meta["file_upload_path"],
                user_details,
            )

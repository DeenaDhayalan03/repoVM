import logging

from ut_security_util import MetaInfoSchema, create_token

from scripts.config import ExternalServices, Secrets
from scripts.constants.api import ExternalAPI
from scripts.utils.common_util import hit_external_service


def deploy_plugin_request(data: dict, user_details: MetaInfoSchema):
    logging.debug("Deploying plugin")
    deploy_url = f"{ExternalServices.PROXY_MANAGER_URL}{ExternalAPI.deploy}"
    cookies = {
        "login-token": create_token(
            project_id=user_details.project_id,
            user_id=user_details.user_id,
            ip=user_details.ip_address,
            token=Secrets.token,
        )
    }
    if resp := hit_external_service(
        api_url=deploy_url,
        request_cookies=cookies,
        headers=cookies,
        payload=data,
        timeout=30,
    ):
        return resp


def delete_container(app_id, plugin_id):
    try:
        delete_api = f"{ExternalServices.PROXY_MANAGER_URL}{ExternalAPI.delete_resources}"
        payload = {"app_name": app_id, "app_id": plugin_id}
        resp = hit_external_service(api_url=delete_api, payload=payload, method="post")
        logging.info(f"Deleted container, Response: {resp}")
    except Exception as e:
        logging.exception(f"Failed to delete container {e}")

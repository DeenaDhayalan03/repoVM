import logging

from scripts.config import MinioSettings
from scripts.constants.ui_components import plugin_registration_types
from scripts.db.mongo.ilens_configurations.collections.constants import Constants
from scripts.utils.minio_util import MinioUtility

plugin_types = {
    "data": [
        {"label": "Widgets", "value": "widget"},
        {"label": "Protocols", "value": "protocols"},
        {"label": "Microservice", "value": "microservice"},
    ],
    "content_type": "pluginTypes",
}

registration_types = {
    "data": [
        {"label": plugin_registration_types["git"], "value": "git"},
        {"label": plugin_registration_types["bundle"], "value": "project_upload"},
        {"label": plugin_registration_types["docker"], "value": "docker"},
    ],
    "content_type": "registrationTypes",
}

dependant_registration_types = {
    "data": {
        "widget": [
            {"label": plugin_registration_types["git"], "value": "git"},
            {
                "label": plugin_registration_types["bundle"],
                "value": "bundle_upload",
            },
        ],
        "protocols": [
            {"label": plugin_registration_types["bundle"], "value": "project_upload"},
        ],
        "microservice": [
            {"label": plugin_registration_types["git"], "value": "git"},
            {"label": plugin_registration_types["bundle"], "value": "bundle_upload", "disabled": True},
            {"label": plugin_registration_types["docker"], "value": "docker", "disabled": True},
        ],
        "content_type": "dependantRegistrationTypes",
    }
}

plugin_list_table_actions = {
    "data": {
        "actions": [
            {
                "action": "register",
                "type": "register",
                "class": "fa-level-up",
                "tooltip": "Register",
            },
            {
                "action": "upload",
                "type": "upload",
                "class": "fa-cloud-upload",
                "tooltip": "Upload to Global catalog",
            },
            {"action": "edit", "type": "edit", "class": "fa-pencil", "tooltip": "Edit"},
            {
                "action": "delete",
                "type": "delete",
                "class": "fa-trash",
                "tooltip": "Delete",
            },
        ],
        "externalActions": [
            {
                "action": "catalog",
                "label": "Import From Catalog",
                "type": "button",
                "icon_class": "",
                "btn_class": "btn-secondary",
            },
            {
                "action": "addnew",
                "label": "Create New",
                "type": "button",
                "icon_class": "fa fa-plus-circle",
                "btn_class": "btn-primary",
            },
        ],
    }
}

plugin_list_table_header = {
    "data": {
        "headerContent": [
            {"headerName": "Plugin Name", "field": "name", "key": "name"},
            {"headerName": "Version", "field": "version", "key": "version"},
            {"headerName": "Plugin Type", "field": "plugin_type", "key": "plugin_type"},
            {
                "headerName": "Status",
                "field": "deployment_status",
                "key": "deployment_status",
            },
        ]
    }
}


def run():
    logging.info("running preflights")
    try:
        constants_conn = Constants()
        constants_conn.update_constants_by_type(
            content_type="registrationTypes",
            data=registration_types,
            update_only_if_not_exist=True,
        )
        constants_conn.update_constants_by_type(
            content_type="pluginTypes", data=plugin_types, update_only_if_not_exist=True
        )
        constants_conn.update_constants_by_type(
            content_type="dependantRegistrationTypes",
            data=dependant_registration_types,
            update_only_if_not_exist=True,
        )
        constants_conn.update_constants_by_type(
            content_type="pluginListTableActions",
            data=plugin_list_table_actions,
            update_only_if_not_exist=True,
        )
        constants_conn.update_constants_by_type(
            content_type="pluginListTableHeader",
            data=plugin_list_table_header,
            update_only_if_not_exist=True,
        )
        logging.info(f"{MinioSettings.MINIO_ENDPOINT} bucket creation")
        MinioUtility(
            endpoint=MinioSettings.MINIO_ENDPOINT,
            access_key=MinioSettings.MINIO_ACCESS_KEY,
            secret_key=MinioSettings.MINIO_SECRET_KEY,
            secure=MinioSettings.MINIO_SECURE,
        ).create_bucket(MinioSettings.MINIO_BUCKET_NAME)
    except Exception as e:
        logging.exception(e)
    finally:
        logging.info("preflight completed")

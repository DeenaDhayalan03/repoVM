import logging

import paho.mqtt.client as mqtt
from pydantic import BaseModel, Field
from ut_notifications_util import PlatformNotificationHandler

from scripts.config import MQTTConf


class NotificationSchema(BaseModel):
    message: str
    type: str = Field("message")
    status: str = "success"
    plugin_type: str
    plugin_id: str | None = None
    download_url: str | None = None


class NotificationSchemaDownload(BaseModel):
    type: str = Field("message")
    message: str
    status: str = "success"
    notification_message: str
    notification_status: str
    report_type: str
    download_link: str
    download_url: str
    mark_as_read: bool = False


def push_notification(notification: NotificationSchema, user_id, project_id):
    catalog_notification = True if project_id.startswith("space_") else False
    PlatformNotificationHandler(project_id).send_notifications(
        type_=notification.type,
        status=notification.status,
        main_msg=notification.message,
        properties={
            "plugin_type": notification.plugin_type,
            "download_url": notification.download_url,
            "plugin_id": notification.plugin_id,
        },
        users=user_id,
        catalog_notification=catalog_notification,
    )


def push_notification_docker_download(notification: NotificationSchemaDownload, user_id, project_id):
    catalog_notification = True if project_id.startswith("space_") else False
    PlatformNotificationHandler(project_id).send_notifications(
        type_=notification.type,
        status=notification.status,
        main_msg=notification.message,
        properties={
            "type": notification.type,
            "download_url": notification.download_url,
            "download_link": notification.download_link,
            "report_type": notification.report_type,
        },
        users=user_id,
        catalog_notification=catalog_notification,
    )


def push_notification_bkp(notification: NotificationSchema, user_id):
    def on_connect(rc):
        if rc == 0:
            logging.info(f"Publisher Connected with result code {str(rc)}")
        else:
            logging.error(f"Failed to connect, return code {str(rc)}")

    def on_publish(mid):
        logging.info(f"Message {mid} published.")

    client = mqtt.Client()
    client.username_pw_set(MQTTConf.MQTT_USERNAME, MQTTConf.MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_publish = on_publish
    try:
        client.connect(MQTTConf.MQTT_URL, MQTTConf.MQTT_PORT, 30)
        topic = f"{MQTTConf.publish_base_topic}/{user_id}/plugins"
        client.publish(topic, notification.model_dump_json(), retain=False, qos=1)
        logging.debug("Notification message published")
    except Exception as e:
        logging.exception(f"Exception at MQTT Publish: {e}")


def push_notification_docker_download_bkp(notification: NotificationSchemaDownload, user_id):
    def on_connect(rc):
        if rc == 0:
            logging.info(f"Publisher Connected with result code {str(rc)}")
        else:
            logging.error(f"Failed to connect, return code {str(rc)}")

    def on_publish(mid):
        logging.info(f"Message {mid} published.")

    client = mqtt.Client()
    client.username_pw_set(MQTTConf.MQTT_USERNAME, MQTTConf.MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_publish = on_publish
    try:
        client.connect(MQTTConf.MQTT_URL, MQTTConf.MQTT_PORT, 30)
        topic = f"{MQTTConf.publish_base_topic}/{user_id}/plugins"
        client.publish(topic, notification.model_dump_json(), retain=False, qos=1)
        logging.debug("Notification message published")
    except Exception as e:
        logging.exception(f"Exception at MQTT Publish: {e}")

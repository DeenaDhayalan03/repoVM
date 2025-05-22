import pytest
from unittest.mock import patch
from scripts.utils.notification_util import push_notification, NotificationSchema


@pytest.fixture
def notification():
    return NotificationSchema(
        message="Test message", type="info", status="successful", plugin_type="test_plugin", plugin_id="1234"
    )


def test_push_notification_successfully(notification):
    with (
        patch("paho.mqtt.client.Client.connect") as mock_connect,
        patch("paho.mqtt.client.Client.publish") as mock_publish,
        patch("paho.mqtt.client.Client.username_pw_set") as mock_username_pw_set,
        patch("logging.debug") as mock_logging,
    ):
        push_notification(notification, "user_id", "project_id")
        mock_connect.assert_called_once()
        mock_publish.assert_called_once()
        mock_username_pw_set.assert_called_once()
        mock_logging.assert_called_with("Notification message published")


def test_push_notification_handles_connection_error(notification):
    with (
        patch("paho.mqtt.client.Client.connect", side_effect=Exception("Connection Error")),
        patch("logging.exception") as mock_logging,
    ):
        push_notification(notification, "user_id", "project_id")
        mock_logging.assert_called_with("Exception at MQTT Publish: Connection Error")

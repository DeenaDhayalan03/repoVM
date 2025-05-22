import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from scripts.utils.decorators import validate_deco, _decode_captcha_exp
from scripts.services.v1.schemas import DefaultFailureResponse

decrypt = "scripts.utils.decorators.AESCipher.decrypt"
validate = "scripts.utils.decorators.JWT.validate"
get_plugin = "scripts.services.v1.handler.plugins.PluginHandler.get_plugin"


@pytest.mark.asyncio
async def test_validate_captcha_valid_request():
    request = MagicMock()
    request.headers.getlist.return_value = []
    request.cookies.get.side_effect = ["encrypted_captcha", "2024-08-19 20:56:09"]
    plugin_data = MagicMock()
    plugin_data.plugin_id = "test_plugin"
    plugin_data.project_id = "test_project"
    plugin_data.captcha = "decrypted_captcha"
    plugin_data.tz = "UTC"
    plugin_data.deployed_on = "2024-08-19 20:56:09"
    kwargs = {"request": request, "plugin_data": plugin_data, "user_id": "test_user", "response": MagicMock()}

    with patch(decrypt, return_value="decrypted_captcha"):
        with patch(validate, return_value={"created_on": "2024-08-19 20:56:09"}):
            with patch(get_plugin, return_value=plugin_data):
                result = await validate_deco(lambda *args, **kwargs: True)(**kwargs)
                assert result


@pytest.mark.asyncio
async def test_validate_captcha_invalid_captcha():
    request = MagicMock()
    request.headers.getlist.return_value = []
    request.cookies.get.side_effect = ["encrypted_captcha", "2024-08-19 20:56:09"]
    plugin_data = MagicMock()
    plugin_data.plugin_id = "test_plugin"
    plugin_data.project_id = "test_project"
    plugin_data.captcha = "wrong_captcha"
    plugin_data.tz = "UTC"
    kwargs = {"request": request, "plugin_data": plugin_data, "user_id": "test_user", "response": MagicMock()}

    with patch(decrypt, return_value="decrypted_captcha"):
        with patch(validate, return_value={"created_on": "2024-08-19 20:56:09"}):
            with patch(get_plugin, return_value=plugin_data):
                result = await validate_deco(lambda *args, **kwargs: True)(**kwargs)
                assert isinstance(result, DefaultFailureResponse)
                assert result.message == "Invalid Captcha Entered"


@pytest.mark.asyncio
async def test_validate_captcha_expired_captcha():
    request = MagicMock()
    request.headers.getlist.return_value = []
    request.cookies.get.side_effect = ["encrypted_captcha", "2024-08-19 20:56:09"]
    plugin_data = MagicMock()
    plugin_data.plugin_id = "test_plugin"
    plugin_data.project_id = "test_project"
    plugin_data.captcha = "decrypted_captcha"
    plugin_data.tz = "UTC"
    kwargs = {"request": request, "plugin_data": plugin_data, "user_id": "test_user", "response": MagicMock()}

    with patch(decrypt, return_value="decrypted_captcha"):
        with patch(
            validate,
            return_value={"created_on": (datetime.now() - timedelta(seconds=4000)).strftime("%Y-%m-%d %H:%M:%S")},
        ):
            with patch(get_plugin, return_value=plugin_data):
                result = await validate_deco(lambda *args, **kwargs: True)(**kwargs)
                assert isinstance(result, DefaultFailureResponse)
                assert result.message


@pytest.mark.asyncio
async def test_validate_captcha_missing_captcha_string():
    request = MagicMock()
    request.headers.getlist.return_value = []
    request.cookies.get.side_effect = [None, "2024-08-19 20:56:09"]
    plugin_data = MagicMock()
    plugin_data.plugin_id = "test_plugin"
    plugin_data.project_id = "test_project"
    plugin_data.captcha = "decrypted_captcha"
    plugin_data.tz = "UTC"
    plugin_data.deployed_on = "2024-08-19 20:56:09"
    kwargs = {"request": request, "plugin_data": plugin_data, "user_id": "test_user", "response": MagicMock()}

    with patch(get_plugin, return_value=plugin_data):
        result = await validate_deco(lambda *args, **kwargs: True)(**kwargs)
        assert isinstance(result, DefaultFailureResponse)
        assert result.message == "Captcha Expired!!"


def test_decode_captcha_exp_valid_token():
    token = "valid_token"
    with patch(validate, return_value={"created_on": "2024-08-19 20:56:09"}):
        result = _decode_captcha_exp(token)
        assert result == datetime.strptime("2024-08-19 20:56:09", "%Y-%m-%d %H:%M:%S")

import copy
import logging
from datetime import datetime
from functools import wraps

from ut_security_util import JWT, AESCipher

from scripts.constants.secrets import Captcha
from scripts.errors import AuthenticationError
from scripts.services.v1.handler.plugins import PluginHandler
from scripts.services.v1.schemas import DefaultFailureResponse, ValidateCaptchaRequest
from scripts.utils.common_util import remove_captcha_cookies, unzip_and_decode_content


def validate_deco(func):  # NOSONAR
    @wraps(func)
    async def validate_captcha(*args, **kwargs):
        try:
            request = kwargs.get("request")
            plugin_data = kwargs.get("plugin_data")
            if plugin_id := plugin_data.plugin_id:
                if project_id := plugin_data.project_id:
                    plugin_handler = PluginHandler(project_id=project_id)
                    plugin = plugin_handler.get_plugin(plugin_id=plugin_id, version=plugin_data.version)
                    if not plugin.deployed_on:
                        return func(*args, **kwargs)
            if "gzip" in request.headers.getlist("Content-Encoding"):
                body = copy.deepcopy(await request.body())
                plugin_data = copy.deepcopy(unzip_and_decode_content(body))
                if not plugin_data.get("plugin_id"):
                    return func(*args, **kwargs)
                input_data = ValidateCaptchaRequest(
                    user_id=kwargs.get("user_id"),
                    captcha=plugin_data.get("captcha"),
                    tz=plugin_data.get("tz"),
                )
            else:
                if not plugin_data:
                    return func(*args, **kwargs)
                input_data = ValidateCaptchaRequest(
                    user_id=kwargs.get("user_id"),
                    captcha=plugin_data.captcha,
                    tz=plugin_data.tz,
                )
            logging.info(f"Cookies: {request.cookies}")
            logging.info(f"Input Data: {input_data}")
            captcha_string = request.cookies.get("captcha_string")
            if not captcha_string:
                raise AuthenticationError("Captcha Expired!!")
            captcha_string = AESCipher(Captcha.captcha_cookie_encryption_key).decrypt(captcha_string)
            if captcha_string == input_data.captcha:
                if "captcha_string_ext" not in request.cookies:
                    logging.debug("Checking if the captcha extension is present")
                    raise AuthenticationError("Captcha Validation failed")
                captcha_time = request.cookies.get("captcha_string_ext")
                captcha_exp_time = _decode_captcha_exp(captcha_time)
                today_with_tz = datetime.now()
                if (today_with_tz - captcha_exp_time).total_seconds() > 3000:
                    logging.debug("Verifying if the captcha is expired")
                    raise AuthenticationError("Captcha Expired!!")
            else:
                raise AuthenticationError("Invalid Captcha Entered")
            if "gzip" in request.headers.getlist("Content-Encoding"):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except AuthenticationError as e:
            return DefaultFailureResponse(message=e.args[0])
        except Exception as e:
            logging.error(str(e))
            return False, str(e.args)
        finally:
            remove_captcha_cookies(kwargs.get("response"))

    return validate_captcha


def _decode_captcha_exp(captcha_time):
    _decoded = JWT().validate(token=captcha_time)
    exp = _decoded.get("created_on")
    return datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")

import logging
import pathlib
from logging import StreamHandler
from logging.handlers import RotatingFileHandler

from scripts.config import PROJECT_NAME, Services


def read_configuration():
    return {
        "name": PROJECT_NAME,
        "handlers": [
            {
                "type": "RotatingFileHandler",
                "max_bytes": 100000000,
                "back_up_count": 5,
                "enable": Services.ENABLE_FILE_LOG,
            },
            {"type": "StreamHandler", "enable": Services.ENABLE_CONSOLE_LOG},
        ],
    }


def init_logger():
    """
    Creates a rotating log
    """
    logging_config = read_configuration()
    __logger__ = logging.getLogger()
    __logger__.setLevel(Services.LOG_LEVEL)
    __logger__.handlers.pop()
    logging.getLogger("httpx").setLevel(logging.WARNING)
    log_formatter = "%(asctime)s - %(levelname)-6s - [%(threadName)5s:%(funcName)5s(): %(lineno)s] - %(message)s"
    time_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_formatter, time_format)
    for each_handler in logging_config["handlers"]:
        if each_handler["type"] in ["RotatingFileHandler"] and each_handler.get("enable", False):
            pathlib.Path("data/logs").mkdir(parents=True, exist_ok=True)
            log_file = pathlib.Path("data/logs", f"{PROJECT_NAME}.log")
            temp_handler = RotatingFileHandler(
                log_file,
                maxBytes=each_handler["max_bytes"],
                backupCount=each_handler["back_up_count"],
            )
            temp_handler.setFormatter(formatter)
        elif each_handler["type"] in ["StreamHandler"] and each_handler.get("enable", True):
            temp_handler = StreamHandler()
            temp_handler.setFormatter(formatter)
        else:
            continue
        __logger__.addHandler(temp_handler)
    return __logger__

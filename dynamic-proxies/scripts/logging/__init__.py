import logging

from scripts.config import EnvConf


def get_logger():
    __logger__ = logging.getLogger("")
    __logger__.setLevel(logging.DEBUG)
    logging.getLogger("kubernetes").setLevel(EnvConf.kubernetes_log_level)

    log_formatter = "%(asctime)s - %(levelname)-6s - [%(threadName)5s:%(funcName)5s(): %(lineno)s] - %(message)s"
    time_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_formatter, time_format)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    __logger__.addHandler(console_handler)

    return __logger__


logger = get_logger()

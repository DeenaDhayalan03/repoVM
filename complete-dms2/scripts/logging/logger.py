import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FILE = "logs/EPR.log"

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("FastAPI-Docker-Manager")
logger.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
console_handler.setLevel(logging.DEBUG)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("Logger initialized successfully")

import logging.config
import pathlib
from logging import Formatter
from logging.handlers import RotatingFileHandler

from tw_frnds_ei.config_app import env_config

LOG_FILE = env_config['APP_LOG_DIR'] + env_config['APP_LOG_FILENAME']
LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s - %(message)s'
LOG_LEVEL = env_config['LOG_LEVEL']

pathlib.Path(env_config['APP_LOG_DIR']).mkdir(parents=True, exist_ok=True)

root_logger = logging.root

if not root_logger.hasHandlers():
    root_logger.setLevel(logging.getLevelName(LOG_LEVEL))
    logging_file_handler = RotatingFileHandler(filename=LOG_FILE,
                                               mode="a",
                                               encoding="UTF-8",
                                               maxBytes=10485760,  # 10MB
                                               backupCount=9)
    logging_file_handler.setFormatter(Formatter(LOG_FORMAT))
    root_logger.addHandler(logging_file_handler)

LOG_BASE_FILE_NAME = root_logger.handlers[0].baseFilename

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("oauthlib").setLevel(logging.WARNING)
logging.getLogger("requests_oauthlib").setLevel(logging.WARNING)

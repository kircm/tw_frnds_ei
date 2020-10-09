import logging.config
import pathlib
from tw_frnds_ei.config_app import env_config

log_levels = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARN': logging.WARNING,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG
}

LOG_FILE = env_config['APP_LOG_DIR'] + env_config['APP_LOG_FILENAME']
LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s - %(message)s'
LOG_LEVEL = log_levels[env_config['LOG_LEVEL']]

pathlib.Path(env_config['APP_LOG_DIR']).mkdir(parents=True, exist_ok=True)

logging.basicConfig(filename=LOG_FILE,
                    filemode='a',
                    format=LOG_FORMAT,
                    level=LOG_LEVEL)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("oauthlib").setLevel(logging.WARNING)
logging.getLogger("requests_oauthlib").setLevel(logging.WARNING)

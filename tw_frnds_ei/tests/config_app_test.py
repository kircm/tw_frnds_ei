import configparser
import logging
import os

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()

path = os.path.dirname(__file__)
path_file = f"{path}/test_config.ini"
logger.info(f"Reading app test config from file: {path_file}")
config.read_file(open(path_file))
test_config = config['TEST']
logger.info(f"Test Config: {dict(test_config)}")

EXP_DATA_DIR = path + "/" + test_config['EXP_DATA_DIR']
logger.info(f"EXP_DATA_DIR: {EXP_DATA_DIR}")
IMP_DATA_DIR = path + "/" + test_config['IMP_DATA_DIR']
logger.info(f"IMP_DATA_DIR: {IMP_DATA_DIR}")

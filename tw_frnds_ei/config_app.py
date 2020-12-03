import configparser
import pathlib

dot_env_file_path = pathlib.Path(__file__).resolve().parents[1].joinpath('.env')

config = configparser.ConfigParser()
config.read_file(open(dot_env_file_path))
env_config = config['DEFAULT']

MAX_NUM_FRIENDS = 3000

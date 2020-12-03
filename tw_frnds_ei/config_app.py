import configparser

config = configparser.ConfigParser()
config.read_file(open('.env'))
env_config = config['DEFAULT']

MAX_NUM_FRIENDS = 3000

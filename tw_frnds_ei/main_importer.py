import argparse
import logging

from twython import Twython

import tw_frnds_ei.config_log as log_conf
import tw_frnds_ei.friends_importer as imp
from tw_frnds_ei.config_app import env_config
from tw_frnds_ei.config_auth import APP_KEY
from tw_frnds_ei.config_auth import APP_SECRET

logger = logging.getLogger(__name__)
logger.info(f"Logging enabled. Log file: {log_conf.LOG_BASE_FILE_NAME}")
logger.info(f"Application config loaded. Importer data dir: {env_config['IMP_DATA_DIR']}")


# ---------------------
# Import main's program
# ---------------------
def main(oauth_user_token, oauth_user_token_secret, csv_file_name):
    print("\nImport process started...")
    print(f"You may check progress in log file: {log_conf.LOG_BASE_FILE_NAME}\n")
    twitter_api_client = Twython(APP_KEY, APP_SECRET, oauth_user_token, oauth_user_token_secret)
    ok, msg, frnds_imported, frnds_remaining = \
        imp.do_import(twitter_api_client, env_config['IMP_DATA_DIR'], csv_file_name)

    if ok:
        print(f"\nThe import finished correctly!\n", msg if msg else "")
    else:
        print("\nERROR when importing: \n", msg)

    if frnds_imported:
        print(f"\nFriendships imported successfully:\n {frnds_imported}")

    if frnds_remaining:
        print(f"\nFriendships not imported:\n {frnds_remaining}")

    return ok, msg, frnds_imported, frnds_remaining


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Import a list of users to follow on Twitter from a CSV file.")
    arg_parser.add_argument("OAUTH_USER_TOKEN")
    arg_parser.add_argument("OAUTH_USER_TOKEN_SECRET")
    arg_parser.add_argument("csv_file_name")
    args = arg_parser.parse_args()
    main(args.OAUTH_USER_TOKEN, args.OAUTH_USER_TOKEN_SECRET, args.csv_file_name)

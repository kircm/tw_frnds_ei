import argparse
import logging

from twython import Twython

import tw_frnds_ei.config_log as log_conf
import tw_frnds_ei.friends_exporter as exp
from tw_frnds_ei.config_app import env_config
from tw_frnds_ei.config_auth import APP_KEY
from tw_frnds_ei.config_auth import APP_SECRET

logger = logging.getLogger(__name__)
logger.info(f"Logging enabled. Log file: {log_conf.LOG_FILE}")
logger.info(f"Application config loaded: {dict(env_config)}")


# ---------------------
# Export main's program
# ---------------------
if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Export the list of users you follow on Twitter to a CSV file.")
    arg_parser.add_argument("OAUTH_USER_TOKEN")
    arg_parser.add_argument("OAUTH_USER_TOKEN_SECRET")
    args = arg_parser.parse_args()

    print("\nExport process started...")
    print(f"You may check progress in log file: {log_conf.LOG_FILE}\n")
    twitter_api_client = Twython(APP_KEY, APP_SECRET, args.OAUTH_USER_TOKEN, args.OAUTH_USER_TOKEN_SECRET)
    ok, msg, file_name = exp.do_export(twitter_api_client, env_config['EXP_DATA_DIR'])

    if ok:
        print("\nThe export finished correctly! Output file:\n", file_name)
    else:
        print("\nERROR when exporting: \n", msg)

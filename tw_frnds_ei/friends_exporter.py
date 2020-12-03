import csv
import logging
import os
import time
from typing import Optional
from typing import Tuple

from pathlib import Path
from twython import Twython
from twython import TwythonError
from twython import TwythonRateLimitError

from tw_frnds_ei.config_app import MAX_NUM_FRIENDS as MAX_NUM_FRIENDS
from tw_frnds_ei.screen_name_logger import ScreenNameLogger
from tw_frnds_ei.waiter import Waiter

logger = logging.getLogger(__name__)


def do_export(cli: Twython, data_dir: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Instantiate a new FriendsExporter and trigger the export process.

    :param cli: A Tython client already containing authentication data
    :type cli: twython.Twython

    :param data_dir: The directory where to drop the CSV file containing the exported data
    :type: data_dir: str

    :return: The result of the process. It includes boolean OK/NOK, potential
    error message for the user, potential file name location (if export successful)
    :rtype: (bool, str, str)
    """
    exporter = FriendsExporter(cli, data_dir)
    exporter.ulog.info("Exporter created!")
    result = exporter.process()
    exporter.ulog.info("Exporter finished!")
    exporter.ulog.info("------------------\n\n")
    return result


class FriendsExporter:
    """A class encapsulating state and methods for producing a CSV file export containing Twitter friends.

    The generated CSV file will contain the user name and user ids of all friends ("followees") of the authenticated
    user.

    :param cli: Twython client already instantiated with authentication tokens
    :type cli: twython.Twython

    :param data_dir: Directory to drop the CSV file into
    :type data_dir: str
    """

    MAX_CURSOR_ITERATIONS = 15  # Max number of data pages to retrieve from Twitter
    RETRY_SLEEP_CHECK_EVERY_SECS = 30  # Number of seconds for the retry waiter to periodically check the clock

    def __init__(self, cli: Twython, data_dir: str) -> None:
        """Constructor.

        Sets attributes passed in and
        * retrieves the twitter user name that corresponds with the OAuth user token
        * instantiates a logger that includes the user name in all logging activity
        """
        self.cli = cli
        self.data_dir = data_dir
        creds = self.cli.verify_credentials(skip_status=True,
                                            include_entities=False,
                                            include_email=False)
        self.user_screen_name = creds['screen_name']
        self.waiter = Waiter(self.user_screen_name)
        self.ulog = ScreenNameLogger(logger=logger, screen_name=self.user_screen_name)

    def process(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """Start the whole export process.

        All the necessary information has been set as instance attributes.

        :return: The result of the process. It includes boolean OK/NOK, potential
        error message for the user, potential file name location (if export successful)
        :rtype: (bool, str, str)
        """
        num_friends_to_export = self._retrieve_num_friends()
        self.ulog.info(f"Number of friends to export: {num_friends_to_export}")

        if num_friends_to_export > MAX_NUM_FRIENDS:
            self.ulog.info(f"{num_friends_to_export} friends to export are too many. Bailing out.")
            user_err_msg = f"{self.user_screen_name} has {num_friends_to_export} friends." + \
                           f" We only support up until {MAX_NUM_FRIENDS}"
            return False, user_err_msg, None

        if num_friends_to_export == 0:
            self.ulog.info("The user is not following any Twitter profile. Bailing out.")
            user_err_msg = f"{self.user_screen_name} is not following anyone. No file generated."
            return False, user_err_msg, None

        else:
            self.ulog.info(
                f"Retrieving data from the user's Twitter profile ({num_friends_to_export} friends).")

            ok, friends_data, user_err_msg = self._retrieve_data_from_twitter()

            if ok:
                self.ulog.info(f"Retrieved {len(friends_data)} friends from the user's Twitter profile.")
                exported_file = self._export_friends_csv(friends_data)
                self.ulog.info(f"Exported CSV file successfully: {exported_file}")
                return True, None, exported_file
            else:
                self.ulog.warn(f"Couldn't export friends data! Message for user: {user_err_msg}")
                return False, user_err_msg, None

    # ---------------
    # private methods
    # ---------------

    def _retrieve_num_friends(self):
        # Check the friends count for authenticated user. If user has too many friends
        # the export will be aborted.
        #
        # Returns: the number of friends (people being followed by) the authenticated user
        self.ulog.debug("Retrieving current user's profile to get friends_count")
        usr = self.cli.show_user(screen_name=self.user_screen_name,
                                 include_entities=False)
        friends_count = usr['friends_count']
        self.ulog.debug(f"Friends count is {friends_count}")
        return friends_count

    def _retrieve_data_from_twitter(self, retried=0, max_retries=1):
        # This method is in charge of controling the data retrieval process
        # from Twitter and managing potential errors raised by the Twitter API.
        #
        # If there is an error indicating we reached the request rate limits
        # we can then inspect the HTTP header that Twitter returns populated
        # with the number of seconds we must wait.
        # The method handles the retry logic, which we set to a small number of
        # max retries given the fact that the process already has waited for
        # Twitter to reset the rate limits.
        #
        # Other errors are treated generically: we bail out of the process
        #
        # Returns: tuple with:
        #  - bool indicating success/failure
        #  - list of friendships retrieved from the user's profile (if successful)
        #  - str with message to show to user (if unsuccessful)
        try:

            friends_data = self._produce_friend_ids_names_list()

        except TwythonRateLimitError as e:
            self.ulog.warn(f"ERROR from Twitter: === {e.error_code} === {e}")
            retried += 1
            if retried <= max_retries:
                self._wait_for_tw_rate_limit_reset(retried, max_retries, self.RETRY_SLEEP_CHECK_EVERY_SECS)
                return self._retrieve_data_from_twitter(retried=retried)
            else:
                self.ulog.warn(f"We reached the maximum number of retries for error code: {e.error_code} "
                               "- Bailing out.")
                return False, None, "We hit the Twitter API request rate limit. You may try again in 24h or so."

        except TwythonError as te:
            self.ulog.warn(f"We got a TwythonError: {te} - Bailing out.")
            return False, None, "There was an error interacting with Twitter. You may try again in 24h or so."

        else:
            self.ulog.info(f"Successfully produced data for {len(friends_data)} friends to export.")
            return True, friends_data, None

    def _produce_friend_ids_names_list(self):
        # This method iterates through the pages of data (indexed by a cursor) that Twitter
        # returns when asked for a user's friends lists. It iterates until Twitter
        # sends an empty next cursor (last page) or until we reach the maximum of iterations
        # supported by this application.
        #
        # Returns: list of dicts containing friendships data.
        #   Each friendship has a user name (screen name) and a user ID
        users, next_cursor = self._get_friends_curs()
        friend_ids_names = []
        condition = True
        iterations = 1
        while condition:
            for u in users:
                friend_ids_names.append((u['screen_name'], u['id']))
            if next_cursor > 0 and iterations <= self.MAX_CURSOR_ITERATIONS:
                users, next_cursor = self._get_friends_curs(curs=next_cursor)
                iterations += 1
            else:
                condition = False

        if iterations > self.MAX_CURSOR_ITERATIONS:
            self.ulog.error(f"Reached {iterations} pagination iterations. This shouldn't happen!")
            raise TwythonError(msg="Too many pages of friends to be retrieved")

        self.ulog.debug(f"Retrieved full list of {len(friend_ids_names)} friends after {iterations} iterations.")
        return friend_ids_names

    def _get_friends_curs(self, curs=None):
        # Retrieve a page of friendship data for a given cursor from Twitter.
        #
        # Returns: tuple with:
        #  - partial list of friends corresponding to the cursor being held by Twitter (or
        #    when no cursor, the first page of data)
        #  - int number for the next cursor, returned by Twitter
        self.ulog.debug(f"Retrieving partial friends list - cursor: {curs}")
        partial_friends_list = self.cli.get_friends_list(
            skip_status=True,
            include_user_entities=False,
            count=200,
            cursor=curs)

        users = partial_friends_list['users']
        next_cursor = partial_friends_list['next_cursor']
        self.ulog.debug(f"Retrieved partial friends list - Num friends: {len(users)} "
                        f"- next cursor: {next_cursor}")
        return users, next_cursor

    def _wait_for_tw_rate_limit_reset(self, retried, max_retries, check_every):
        # Sleep until we reach Twitter's API request rate limit reset time and return
        reset = int(self.cli.get_lastfunction_header('x-rate-limit-reset'))
        wait_until = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(reset))
        self.ulog.info(f"Waiting until {wait_until}...")
        self.waiter.sleep_until(reset, check_every)
        self.ulog.info(f"Retrying... ({retried}/{max_retries})")

    def _generate_csv_file_name(self):
        # Generate a unique CSV file name using the current authenticated Twitter user and a timestamp.
        #
        # Returns: an str with the file name to be created
        curr_timestamp_ns = str(time.time_ns())
        return f"friends_{self.user_screen_name}_{curr_timestamp_ns}.csv"

    def _export_friends_csv(self, friends):
        # Dump friendship data to a file in CSV format
        #
        # Returns: str of the full absolute path and file name of the generated CSV file
        data_path = Path(self.data_dir).joinpath(self.user_screen_name).resolve()
        data_path.mkdir(parents=True, exist_ok=True)
        data_path_file = data_path.joinpath(self._generate_csv_file_name())

        self.ulog.debug(f"Starting data export of {len(friends)} friends "
                        f"to file {data_path_file}")
        with open(data_path_file, 'w', newline='') as csv_file:
            full_path_file_name = os.path.realpath(csv_file.name)
            writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
            for tup in friends:
                writer.writerow([tup[0], tup[1]])
        self.ulog.debug(f"Exported {len(friends)} friends to CSV file with relative path {data_path_file}")
        return full_path_file_name

# **** EOC

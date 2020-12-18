import copy
import csv
import logging
import random
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from twython import Twython
from twython import TwythonError

from tw_frnds_ei.config_app import MAX_NUM_FRIENDS
from tw_frnds_ei.screen_name_logger import ScreenNameLogger
from tw_frnds_ei.waiter import Waiter

logger = logging.getLogger(__name__)


def do_import(cli: Twython, data_dir: str, csv_file_name: str) \
        -> Tuple[bool, str, Optional[List[str]], Optional[List[Dict[str, str]]]]:
    """Instantiate a new FriendsImporter and trigger the import process.

    :param cli: A Tython client already containing authentication data
    :type cli: twython.Twython

    :param data_dir: The directory where to look for the CSV file to import
    :type: data_dir: str

    :param csv_file_name: The CSV file name to import
    :type: csv_file_name: str

    :return: The result of the process. It includes boolean OK/NOK, potential
    message for the user with further details, potential list of friends that could
    not be imported
    :rtype: (bool, str, list)
    """
    importer = FriendsImporter(cli, data_dir, csv_file_name)
    importer.ulog.info("Importer created!")
    result = importer.process()
    importer.ulog.info("Importer finished!")
    importer.ulog.info("------------------\n\n")
    return result


class FriendsImporter:
    """A class encapsulating state and methods for importing Twitter friendships read from a CSV file.

    The CSV file should list the Twitter user names and user ids that are to be followed by the authenticated user.

    :param cli: Twython client already instantiated with authentication tokens
    :type cli: twython.Twython

    :param data_dir: Directory to read CSV file from
    :type data_dir: str

    :param csv_file_name: Name of the CSV file to import
    :type csv_file_name: str
    """

    MAX_CSV_ROWS = MAX_NUM_FRIENDS
    RETRY_SHORT_SECONDS_TO_WAIT = 300  # 5 minutes
    RETRY_LONG_SECONDS_TO_WAIT = 900  # 15 minutes
    RETRY_SLEEP_CHECK_EVERY_SECS = 30  # Number of seconds for the retry waiter to periodically check the clock
    MAX_FRIEND_REQUESTS_PER_DAY = 400  # Respect Twitter's daily limits on following accounts
    THROTTLE_SLEEP_CHECK_EVERY_SECS = 30  # Number of seconds the throttler will periodically check the clock

    def __init__(self, cli: Twython, data_dir: str, csv_file_name: str) -> None:
        """Constructor.

        Sets attributes passed in and
        * retrieves the twitter user name that corresponds with the OAuth user token
        * instantiates a logger that includes the user name in all logging activity
        """
        self.cli = cli
        self.data_dir = data_dir
        self.csv_file_name = csv_file_name
        creds = self.cli.verify_credentials(skip_status=True,
                                            include_entities=False,
                                            include_email=False)
        self.user_screen_name = creds['screen_name']
        self.waiter = Waiter(self.user_screen_name)
        self.ulog = ScreenNameLogger(logger=logger, screen_name=self.user_screen_name)

    def process(self) -> Tuple[bool, Optional[str], Optional[List[str]], Optional[List[Dict[str, str]]]]:
        """Start the whole import process.

        All the necessary information has been set as instance attributes.

        :return: The result of the process. It includes boolean OK/NOK, potential
        message for the user with further details, potential list of friends
        that were imported and potential list of friends that could not be imported.
        :rtype: (bool, str, str, list)
        """
        ok, friends_data, err_msg = self._load_friends_data()
        if not ok:
            # couldn't even load data from the CSV file
            return False, err_msg, None, None

        self.ulog.info(f"Importing {len(friends_data)} friends.")
        ok, screen_names_imported, friendships_remaining, err_msg_details_for_user = \
            self._throttle_friendship_requests(friends_data=friends_data)

        if ok:
            self.ulog.info(f"Importer succeeded! Imported {len(screen_names_imported)} friends.")
            return True, None, screen_names_imported, friendships_remaining
        else:
            self.ulog.info("Importer couldn't finish properly.")
            msg = self._build_user_message_process_unfinished(err_msg_details_for_user, screen_names_imported)
            return False, msg, screen_names_imported, friendships_remaining

    # ---------------
    # private methods
    # ---------------

    def _load_friends_data(self):
        # Try to load the CSV file into a list of dict data structure.
        # Handle potential errors
        #
        # Returns: tuple with:
        #  - bool indicating success/failure
        #  - a list of dicts containing twitter user names and user ids (if successful)
        #  - str potential message for the end user (if unsuccessful)
        try:
            self.ulog.info(f"Loading CSV file: {self.csv_file_name}")

            friends_data = self._load_friends_csv()

            self.ulog.info(f"Loaded CSV file: {self.csv_file_name}")

        except IndexError:
            self.ulog.warn(f"Bad CSV file! -> {self.csv_file_name}")
            return False, None, "Bad CSV file!"

        except EmptyFileError:
            msg = f"Empty CSV file: {self.csv_file_name}"
            self.ulog.warn(msg)
            error_msg_for_user = msg
            return False, None, error_msg_for_user

        except FileTooBigError as too_big:
            self.ulog.warn(f"File too big. We stopped at the row number {too_big.last_row}. "
                           f"CSV file: {self.csv_file_name}")
            error_msg_for_user = f"The CSV file is too big. We stopped reading it at the " \
                                 f"row number {too_big.last_row}. The limit is {self.MAX_CSV_ROWS}"
            return False, None, error_msg_for_user

        return True, friends_data, None

    def _load_friends_csv(self):
        # Open and read all lines of the CSV file in path
        # May raise exception when too many rows have been read
        #
        # Returns: a list of dicts containing twitter user names and user ids
        data_path = Path(self.data_dir).joinpath(self.user_screen_name).resolve()
        data_path_file = data_path.joinpath(self.csv_file_name)

        self.ulog.debug(f"Loading friends from CSV file: {data_path_file}")
        friends_data = []
        with open(data_path_file, 'r', newline='') as csv_file:
            reader = csv.reader(csv_file, delimiter=',', quotechar='"')
            row_number = 1
            for row in reader:
                if row_number > self.MAX_CSV_ROWS:
                    raise FileTooBigError(row_number)
                fr_name = row[0]
                fr_id = int(row[1])
                friends_data.append({'screen_name': fr_name, 'fr_id': fr_id})
                row_number += 1

        self.ulog.debug(f"Successfully loaded {len(friends_data)} friends to import "
                        f"from CSV file {data_path_file}")
        if not friends_data:
            raise EmptyFileError()

        return friends_data

    def _throttle_friendship_requests(self, friends_data):
        # This method is in charge of looping through the friendships to be imported
        # and creating a friendship for each one of them (make the authenticated twitter user
        # follow another user ("friend")). After a successful friendship creation it delegates
        # to the waiter to wait for a certain period of time to throttle the requests sent to
        # Twitter.
        #
        # Returns: tuple with:
        #  - bool indicating success/failure
        #  - list of user names sucessfully imported as friends
        #  - list of friendships that could not be imported as friends
        #  - str potential message for the end user
        num_friends = len(friends_data)
        self.ulog.info(f"Starting the creation of {num_friends} friendships...")
        friendships_remaining = copy.deepcopy(friends_data)
        screen_names_imported = []
        for friendship_to_import in friends_data:

            ok, error_msg_for_user, reason_for_skipping = self._create_friendship(friendship_to_import)

            if ok:
                self.ulog.debug(f"Appending imported friendship: {friendship_to_import} to log.")
                screen_names_imported.append(friendship_to_import['screen_name'])
                self.ulog.debug(f"Removing imported friendship: {friendship_to_import} from remaining.")
                friendships_remaining.remove(friendship_to_import)
                self._wait_for_next(num_friends)

            elif reason_for_skipping:
                idx = friendships_remaining.index(friendship_to_import)
                friendships_remaining[idx]['reason_for_skipping'] = reason_for_skipping
                self._wait_for_next(num_friends)

            else:
                self.ulog.warn("Problem importing friendships!")
                if screen_names_imported:
                    self.ulog.warn(f"Still were able to import {len(screen_names_imported)} friends")
                self.ulog.debug(f"Imported user screen names: {screen_names_imported}")
                self.ulog.debug(f"Error message for user: {error_msg_for_user}")
                return False, screen_names_imported, friendships_remaining, error_msg_for_user

        self.ulog.info(f"Created {len(screen_names_imported)} friendships sucessfully!")
        self.ulog.debug(f"Imported user screen names: {screen_names_imported}")
        return True, screen_names_imported, friendships_remaining, None

    def _wait_for_next(self, num_friends):
        # calculate seconds to wait to throttle requests
        seconds_to_wait, check_every = self._throttle_seconds_to_wait(num_friends)
        self.ulog.info(f"Throttle: waiting for {seconds_to_wait} seconds...")
        self.waiter.sleep_for(seconds_to_wait, check_every)
        self.ulog.info("Throttle: resuming activity")

    def _throttle_seconds_to_wait(self, num_friends):
        # Calculate the number of seconds to wait depending on the size of the
        # data to import. Add some randomization.
        #
        # Returns: tuple with:
        #   - seconds to wait
        #   - seconds to check the clock periodically
        if num_friends > self.MAX_FRIEND_REQUESTS_PER_DAY:
            # have a bit of a randomization when waiting while ensuring
            # we stick to the daily limit.
            lower_bound = int(24 * 3600 / self.MAX_FRIEND_REQUESTS_PER_DAY)
            upper_bound = int(25 * 3600 / self.MAX_FRIEND_REQUESTS_PER_DAY)
            check_every = self.THROTTLE_SLEEP_CHECK_EVERY_SECS
        else:
            # Small waiting time to avoid surpassing 30 follow requests per minute
            lower_bound = 2
            upper_bound = 3
            check_every = 1

        return random.randint(lower_bound, upper_bound), check_every

    def _create_friendship(self, friendship_to_import, retried=0, max_retries=3):
        # Try to create a friendship with a Twitter user, handle potential errors,
        # implement retry logic. This method talks to the Tython client, which
        # posts create_friendship requests to the Twitter API.
        #
        # Returns: tuple with:
        #   - bool indicating success/failure
        #   - str potential message for the end user
        screen_name = friendship_to_import['screen_name']
        fr_id = friendship_to_import['fr_id']
        self.ulog.debug(f"Creating friendship with {screen_name}")
        try:

            self.cli.create_friendship(user_id=fr_id)

            self.ulog.info(f"Created friendship with: {screen_name} | ID: {fr_id}")
            return True, None, None

        except TwythonError as e:
            self.ulog.warn(f"ERROR from Twitter: === {e.error_code} === {e}")
            retry, reason_for_skipping, irrecoverable_error = self._decide_if_retry(friendship_to_import, e)
            if retry:
                retried += 1
                return self._handle_retry(friendship_to_import,
                                          retried,
                                          max_retries)
            elif irrecoverable_error:
                return False, irrecoverable_error, None
            else:
                return False, None, reason_for_skipping

    def _decide_if_retry(self, friendship_to_import, err):
        screen_name = friendship_to_import['screen_name']
        is_data_error, reason_for_skipping, irrecoverable_error = self._parse_twithon_error(err, screen_name)

        if is_data_error:
            self.ulog.debug(f"Skipping import of {screen_name} due to: '{reason_for_skipping}'")
            return False, reason_for_skipping, None
        elif irrecoverable_error:
            self.ulog.warn(f"We got an error that we can't recover from! Stopping process! Error: {err.msg}")
            return False, None, irrecoverable_error
        else:
            self.ulog.debug(f"Will retry import of {screen_name}")
            return True, None, None

    def _handle_retry(self,
                      friendship_to_import,
                      retried,
                      max_retries):
        # Helper method to handle the retrying logic.
        # After parsing the text of a Twitter error message we can have several scenarios:
        #
        #  - The error raised indicates a problem with the data related to the
        #    friendship being imported -> Don't retry and report the message to be
        #    shown to the user
        #
        #  - The error is not about the data but (possibly) API rate limits reached
        #    and we haven't reached the max number of retries yet -> wait and retry
        #
        #  - The error is not about the data but (possibly) API rate limits reached
        #    and we have reached the max number of retries exactly, meaning,
        #    this is the last retry -> do a very long wait (around 24 hours) to
        #    clear the twitter daily limit and retry for the last time
        #
        #  - The error is not about the data but (possibly) API rate limits reached
        #    and we have exhausted all retries, including the long one -> Don't retry,
        #    abort the import.
        #
        # Returns: tuple with:
        #  - bool indicating success/failure
        #  - str potential message for the end user
        if retried < max_retries:
            seconds_to_wait = self.RETRY_SHORT_SECONDS_TO_WAIT * retried
            self.ulog.info(f"Waiting for {seconds_to_wait} seconds...")
            self.waiter.sleep_for(seconds_to_wait, self.RETRY_SLEEP_CHECK_EVERY_SECS)
            self.ulog.info(f"Retrying... ({retried}/{max_retries})")
            return self._create_friendship(friendship_to_import, retried=retried, max_retries=max_retries)

        elif retried == max_retries:
            seconds_to_wait = self.RETRY_LONG_SECONDS_TO_WAIT
            self.ulog.info(
                f"We reached the max number of retries: {max_retries} when trying to create friendship "
                f"with {friendship_to_import}. We will have sleep for a longer time: {seconds_to_wait} seconds!")
            self.ulog.info(f"Waiting for {seconds_to_wait} seconds...")
            self.waiter.sleep_for(seconds_to_wait, self.RETRY_SLEEP_CHECK_EVERY_SECS)
            self.ulog.info(f"Retrying... ({retried}/{max_retries})")
            return self._create_friendship(friendship_to_import, retried=retried, max_retries=max_retries)

        else:
            self.ulog.warn(f"OK, we retried to create friendship with {friendship_to_import} "
                           f"for the last time after {self.RETRY_LONG_SECONDS_TO_WAIT} seconds. "
                           "We are bailing out!")
            return False, "Retried too many times", None

    def _parse_twithon_error(self, err, screen_name):
        # Very simple, naive parsing of an actual error string returned by Twitter.
        # It only recognizes the situations (that we know of) that requires the user to modify
        # the CSV file to remove a row that cannot and will not ever be imported.
        #
        # Returns: tuple with:
        #   - bool indicating if there is a required action to be taken by the end user to fix the data
        #   - str potential message for the end user
        skip_import = False
        reason_for_skipping = None

        cannot_find_user_err: bool = err.msg.find("Cannot find specified user") >= 0
        you_are_blocked_by_user_err: bool = err.msg.find("You have been blocked") >= 0
        already_requested_user: bool = err.msg.find("already requested to follow") >= 0
        unauthorized: bool = err.msg.find("401 (Unauthorized), Invalid or expired token") >= 0

        if cannot_find_user_err or you_are_blocked_by_user_err or already_requested_user:
            skip_import = True
            self.ulog.debug(f"Parsed Twitter error message and it indicates problem with the data. "
                            f"Err msg: |{err.msg}|")
        else:
            self.ulog.debug(f"Parsed Twitter error message and it's not indicative of a problem with the data. "
                            f"Err msg: |{err.msg}|")

        if cannot_find_user_err:
            reason_for_skipping = \
                f"The twitter user: {screen_name} could not be followed - It doesn't exist anymore!"
        elif you_are_blocked_by_user_err:
            reason_for_skipping = \
                f"The twitter user: {screen_name} could not be followed - They blocked your account from " \
                "following them!"
        elif already_requested_user:
            reason_for_skipping = \
                f"The twitter user: {screen_name} could not be followed - The account is protected."

        if skip_import:
            return True, reason_for_skipping, None

        if unauthorized:
            irrecoverable_error = \
                f"The twitter importer application is not authorized to act on {self.user_screen_name}'s behalf anymore"
            return False, None, irrecoverable_error
        else:
            return False, None, None

    def _build_user_message_process_unfinished(self, err_msg_details_for_user, screen_names_imported):
        # Build a message for the user after the import process was unsuccessful. There could
        # be friendships that were successfully imported and there could be specific details
        # to include in the message
        #
        # Returns: A str of the message to be shown to the end user including details about
        #   potential solutions: remove rows from CSV and re-submit file, try again in 24h, etc
        msg = f"Sorry, {self.user_screen_name} we couldn't follow all the people listed in the CSV file. "

        if len(screen_names_imported) > 0:
            self.ulog.info(f"But Importer was able to import {len(screen_names_imported)} friends. "
                           f"These: {screen_names_imported}")
            msg += f"But we added these ({len(screen_names_imported)}): " + \
                   f"\n{screen_names_imported}\n"

        msg += "- More details:\n"
        if err_msg_details_for_user:
            msg += "- " + err_msg_details_for_user + "\n"
        else:
            msg += "- You may remove the accounts that were successfully imported from the CSV file " + \
                   "and try again in 24h or so.\n" + \
                   "- Twitter API has daily and hourly limits for following people.\n" + \
                   "- It's quite possible we hit a limit eventhough we tried to pace the requests.. :-("
        return msg

# **** EOC


class FileTooBigError(Exception):
    def __init__(self, last_row):
        self.last_row = last_row


# **** EOC


class EmptyFileError(Exception):
    def __init__(self):
        super().__init__()

# **** EOC

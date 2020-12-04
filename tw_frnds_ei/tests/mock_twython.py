import logging
import time

from twython import TwythonError
from twython import TwythonRateLimitError

logger = logging.getLogger(__name__)


class MockTwython:
    SCENARIO_OK = "SCENARIO_OK"
    SCENARIO_RETRY_OK = "SCENARIO_RETRY_OK"
    SCENARIO_RETRY_NOK = "SCENARIO_RETRY_NOK"
    SCENARIO_NOK = "SCENARIO_NOK"
    SCENARIO_SKIP = "SCENARIO_SKIP"
    SCENARIO_ABORT = "SCENARIO_ABORT"

    def __init__(self, user, scenario):
        self.user = user
        self.scenario = scenario
        self.num_friends = None
        self.data_pages = None
        self.page_err = None
        self.next_retry_ok = False
        self.user_id_err = None

    def verify_credentials(self, **kwargs):
        return {"screen_name": self.user}

    def show_user(self, **kwargs):
        return {"friends_count": self.num_friends}

    def get_friends_list(self, **kwargs):
        users = []
        for p in range(10):
            users.append({'screen_name': f"name{self.data_pages}{p}", 'id': 12345 + self.data_pages + p})

        if self.scenario == self.SCENARIO_OK:
            return self._get_friends_list_page_ok(users)
        elif self.scenario == self.SCENARIO_RETRY_OK:
            return self._get_friends_list_page_retry_ok(users)
        elif self.scenario == self.SCENARIO_RETRY_NOK:
            return self._get_friends_list_page_retry_nok(users)
        elif self.scenario == self.SCENARIO_NOK:
            return self._get_friends_list_page_nok(users)
        else:
            raise ValueError(f"MockTython has been set with invalid scenario: {self.scenario}")

    @staticmethod
    def get_lastfunction_header(*args):
        logger.info(f"header: {args}")
        logger.info(f"time: {int(time.time())}")
        return int(time.time()) + 2

    def create_friendship(self, **kwargs):
        user_id_to_follow = kwargs['user_id']
        logger.info(f"create_friendship with user_id: {user_id_to_follow}")

        if self.scenario == self.SCENARIO_OK:
            return None
        elif self.scenario == self.SCENARIO_RETRY_OK:
            if user_id_to_follow == self.user_id_err and not self.next_retry_ok:
                self.next_retry_ok = True
                raise TwythonRateLimitError(error_code=403, msg="Can retry")
            return None
        elif self.scenario == self.SCENARIO_RETRY_NOK:
            if user_id_to_follow == self.user_id_err:
                raise TwythonRateLimitError(error_code=403, msg="Too many retries")
            return None
        elif self.scenario == self.SCENARIO_SKIP:
            if user_id_to_follow == self.user_id_err:
                raise TwythonError("Cannot find specified user")
            return None
        elif self.scenario == self.SCENARIO_ABORT:
            if user_id_to_follow == self.user_id_err:
                raise TwythonError("401 (Unauthorized), Invalid or expired token")
            return None

        else:
            raise ValueError(f"MockTython has been set with invalid scenario: {self.scenario}")

    # ---------------
    # Private methods
    # ---------------
    def _get_friends_list_page_ok(self, users):
        self.data_pages -= 1
        if self.data_pages > 0:
            next_cursor = 1234
        else:
            next_cursor = -1

        result = {'users': users, 'next_cursor': next_cursor}
        return result

    def _get_friends_list_page_retry_ok(self, users):
        error_to_raise = TwythonRateLimitError(error_code=403, msg="Can retry")
        self.data_pages -= 1
        next_cursor = self._process_cursor(error_to_raise)
        result = {'users': users, 'next_cursor': next_cursor}
        return result

    def _get_friends_list_page_retry_nok(self, users):
        error_to_raise = TwythonRateLimitError(error_code=403, msg="Too many retries")
        self.data_pages = self.page_err
        next_cursor = self._process_cursor(error_to_raise)
        result = {'users': users, 'next_cursor': next_cursor}
        return result

    def _get_friends_list_page_nok(self, users):
        error_to_raise = TwythonError("Irrecoverable error!")
        self.data_pages -= 1
        next_cursor = self._process_cursor(error_to_raise)
        result = {'users': users, 'next_cursor': next_cursor}
        return result

    def _process_cursor(self, error_to_raise):
        if self.data_pages == self.page_err:
            raise error_to_raise
        elif self.data_pages > 0:
            next_cursor = 1234
        else:
            next_cursor = -1
        return next_cursor

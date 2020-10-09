import logging
import time

from tw_frnds_ei.screen_name_logger import ScreenNameLogger

logger = logging.getLogger(__name__)


class Waiter:
    """A Waiter instance contains the logic to pause the program's execution while keeping an eye on the clock.

    A waiter needs to be instantiated

    """
    def __init__(self, user_screen_name):
        self.user_screen_name = user_screen_name
        self.initial = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(time.time())))
        self.user_logger = ScreenNameLogger(logger=logger, screen_name=self.user_screen_name)

    def sleep_for(self, seconds_to_wait: int, check_every: int) -> None:
        now = int(time.time())
        time_to_wake_up = now + seconds_to_wait
        self.sleep_until(time_to_wake_up, check_every)

    def sleep_until(self, time_to_wake_up: int, check_every: int) -> None:
        sleep_until = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_to_wake_up))
        while True:
            now = int(time.time())
            seconds_remaining = time_to_wake_up - now
            self.user_logger.debug(f"Still {seconds_remaining} seconds to wait until {sleep_until}. "
                                   f"Initial time was {self.initial}")

            if seconds_remaining <= 0:
                break
            else:
                time.sleep(check_every)
                self.user_logger.debug(f"Checking current time - Doing this every {check_every} seconds.")

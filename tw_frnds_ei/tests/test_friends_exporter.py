import logging

from tw_frnds_ei.friends_exporter import FriendsExporter
from tw_frnds_ei.tests.config_app_test import EXP_DATA_DIR

logger = logging.getLogger(__name__)


# -----------------------
# Tests
# -----------------------

def test_exporter_fails_zero_friends(tw_client_ok):
    logger.info("---------- test_exporter_fails_zero_friends ----------")
    user_name = "zero_friends"
    num_friends = 0
    tw_client = tw_client_ok(user_name, num_friends=num_friends)
    exporter = FriendsExporter(tw_client, EXP_DATA_DIR)

    ok, msg, file_name = exporter.process()

    assert not ok
    assert msg
    assert file_name is None
    logger.info("========== test_exporter_fails_zero_friends ============")


def test_exporter_fails_too_many_friends(tw_client_ok):
    logger.info("---------- test_exporter_fails_too_many_friends ----------")
    user_name = "too_many_friends"
    num_friends = 3001
    tw_client = tw_client_ok(user_name, num_friends=num_friends)
    exporter = FriendsExporter(tw_client, EXP_DATA_DIR)

    ok, msg, file_name = exporter.process()

    assert not ok
    assert msg
    assert file_name is None
    logger.info("========== test_exporter_fails_too_many_friends ============")


def test_exports_friends_several_pages(tw_client_ok):
    logger.info("---------- test_exports_friends_several_pages ----------")
    user_name = "jack"
    num_friends = 40
    data_pages = 4
    tw_client = tw_client_ok(user_name, num_friends=num_friends, data_pages=data_pages)
    exporter = FriendsExporter(tw_client, EXP_DATA_DIR)

    ok, msg, file_name = exporter.process()

    assert exporter.user_screen_name == user_name, f"Should be {user_name}"
    assert ok
    assert msg is None
    assert file_name.find(user_name) > 0
    with open(file_name, 'r') as csv_file:
        lines = csv_file.readlines()
        assert len(lines) == tw_client.num_friends
    logger.info("========== test_exports_friends_several_pages ============")


def test_exporter_retries_ok(tw_client_ok_retries):
    logger.info("---------- test_exporter_retries_ok ----------")
    user_name = "retrying_user"
    num_friends = 40
    data_pages = 4
    page_err = 2
    tw_client = tw_client_ok_retries(user_name, num_friends=num_friends, data_pages=data_pages, page_err=page_err)
    exporter = FriendsExporter(tw_client, EXP_DATA_DIR)
    exporter.RETRY_SLEEP_CHECK_EVERY_SECS = 3

    ok, msg, file_name = exporter.process()

    assert ok
    assert msg is None
    assert file_name.find(user_name) > 0
    with open(file_name, 'r') as csv_file:
        lines = csv_file.readlines()
        assert len(lines) > 0
    logger.info("========== test_exporter_retries_ok ============")


def test_exporter_irrecoverable_twitter_err(tw_client_nok):
    logger.info("---------- test_exporter_irrecoverable_twitter_err ----------")
    user_name = "erroring_user"
    num_friends = 40
    data_pages = 4
    page_err = 2
    tw_client = tw_client_nok(user_name, num_friends=num_friends, data_pages=data_pages, page_err=page_err)
    exporter = FriendsExporter(tw_client, EXP_DATA_DIR)
    exporter.RETRY_SLEEP_CHECK_EVERY_SECS = 3

    ok, msg, file_name = exporter.process()

    assert not ok
    assert msg
    assert file_name is None
    logger.info("========== test_exporter_irrecoverable_twitter_err ============")

import logging

from tw_frnds_ei.friends_importer import FriendsImporter
from tw_frnds_ei.tests.config_app_test import IMP_DATA_DIR

logger = logging.getLogger(__name__)


# -----------------------
# Tests
# -----------------------

def test_importer_fails_csv_file_bad(tw_client_ok):
    logger.info("---------- test_importer_fails_csv_file_bad ----------")
    user_name = "bad_csv"
    mock_client = tw_client_ok(user_name)
    importer = FriendsImporter(mock_client, IMP_DATA_DIR, "bad_csv.csv")

    ok, msg, friendships_remaining = importer.process()

    assert not ok
    assert msg.find("Bad CSV") >= 0
    assert not friendships_remaining
    logger.info("========== test_importer_fails_csv_file_bad ============")


def test_importer_fails_csv_file_too_big(tw_client_ok):
    logger.info("---------- test_importer_fails_csv_file_too_big ----------")
    user_name = "csv_too_big"
    mock_client = tw_client_ok(user_name)
    importer = FriendsImporter(mock_client, IMP_DATA_DIR, "csv_too_big.csv")
    importer.MAX_CSV_ROWS = 10

    ok, msg, friendships_remaining = importer.process()

    assert not ok
    assert msg.find("CSV file is too big") >= 0
    assert not friendships_remaining
    logger.info("========== test_importer_fails_csv_file_too_big ============")


def test_importer_fails_csv_empty(tw_client_ok):
    logger.info("---------- test_importer_fails_csv_empty ----------")
    user_name = "empty_csv"
    mock_client = tw_client_ok(user_name)
    importer = FriendsImporter(mock_client, IMP_DATA_DIR, "empty_csv.csv")

    ok, msg, friendships_remaining = importer.process()

    assert not ok
    assert msg.find("Empty CSV file") >= 0
    assert not friendships_remaining
    logger.info("========== test_importer_fails_csv_empty ============")


def test_importer_imports_ok(tw_client_ok):
    logger.info("---------- test_importer_imports_ok ----------")
    user_name = "importing_user"
    mock_client = tw_client_ok(user_name)
    importer = FriendsImporter(mock_client, IMP_DATA_DIR, "good_csv.csv")

    ok, msg, friendships_remaining = importer.process()

    assert importer.user_screen_name == user_name, f"Should be {user_name}"
    assert ok
    assert msg.find("we added") >= 0
    assert not friendships_remaining
    logger.info("========== test_importer_imports_ok ============")


def test_importer_retries_ok(tw_client_ok_retries):
    logger.info("---------- test_importer_retries_ok ----------")
    user_name = "retry_user"
    user_id_err = 12349  # this user id will fail in the mock twython client
    mock_client = tw_client_ok_retries(user_name, user_id_err=user_id_err)
    importer = FriendsImporter(mock_client, IMP_DATA_DIR, "good_csv.csv")
    importer.RETRY_SLEEP_CHECK_EVERY_SECS = 4
    importer.RETRY_SHORT_SECONDS_TO_WAIT = 6
    importer.RETRY_LONG_SECONDS_TO_WAIT = 10

    ok, msg, friendships_remaining = importer.process()

    assert ok
    assert msg.find("we added") >= 0
    assert not friendships_remaining
    logger.info("========== test_importer_retries_ok ============")


def test_importer_irrecoverable_twitter_err(tw_client_nok):
    logger.info("---------- test_importer_irrecoverable_twitter_err ----------")
    user_name = "erroring_user"
    user_id_err = 12349  # this user id will fail in the mock twython client
    mock_client = tw_client_nok(user_name, user_id_err=user_id_err)
    importer = FriendsImporter(mock_client, IMP_DATA_DIR, "good_csv.csv")
    importer.RETRY_SLEEP_CHECK_EVERY_SECS = 4
    importer.RETRY_SHORT_SECONDS_TO_WAIT = 6
    importer.RETRY_LONG_SECONDS_TO_WAIT = 10

    ok, msg, friendships_remaining = importer.process()

    assert not ok
    assert msg.find("Sorry") >= 0
    assert msg.find("we couldn't follow") >= 0
    assert len(friendships_remaining) == 4
    assert friendships_remaining[0]['screen_name'] == "name22"
    logger.info("========== test_importer_irrecoverable_twitter_err ============")

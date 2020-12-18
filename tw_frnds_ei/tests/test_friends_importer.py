import logging

from twython import TwythonError

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
    importer = FriendsImporter(mock_client, IMP_DATA_DIR, "bad_csv.test_csv")

    ok, msg, frnds_imported, frnds_remaining = importer.process()

    assert not ok
    assert msg.find("Bad CSV") >= 0
    assert not frnds_imported
    assert not frnds_remaining
    logger.info("========== test_importer_fails_csv_file_bad ============")


def test_importer_fails_csv_file_too_big(tw_client_ok):
    logger.info("---------- test_importer_fails_csv_file_too_big ----------")
    user_name = "csv_too_big"
    mock_client = tw_client_ok(user_name)
    importer = FriendsImporter(mock_client, IMP_DATA_DIR, "csv_too_big.test_csv")
    importer.MAX_CSV_ROWS = 10

    ok, msg, frnds_imported, frnds_remaining = importer.process()

    assert not ok
    assert msg.find("CSV file is too big") >= 0
    assert not frnds_imported
    assert not frnds_remaining
    logger.info("========== test_importer_fails_csv_file_too_big ============")


def test_importer_fails_csv_empty(tw_client_ok):
    logger.info("---------- test_importer_fails_csv_empty ----------")
    user_name = "empty_csv"
    mock_client = tw_client_ok(user_name)
    importer = FriendsImporter(mock_client, IMP_DATA_DIR, "empty_csv.test_csv")

    ok, msg, frnds_imported, frnds_remaining = importer.process()

    assert not ok
    assert msg.find("Empty CSV file") >= 0
    assert not frnds_imported
    assert not frnds_remaining
    logger.info("========== test_importer_fails_csv_empty ============")


def test_importer_imports_ok(tw_client_ok):
    logger.info("---------- test_importer_imports_ok ----------")
    user_name = "importing_user"
    mock_client = tw_client_ok(user_name)
    importer = FriendsImporter(mock_client, IMP_DATA_DIR, "good_csv.test_csv")

    ok, msg, frnds_imported, frnds_remaining = importer.process()

    assert importer.user_screen_name == user_name, f"Should be {user_name}"
    assert ok
    assert not msg
    assert len(frnds_imported) == 6
    assert not frnds_remaining
    logger.info("========== test_importer_imports_ok ============")


def test_importer_retries_ok(tw_client_ok_retries):
    logger.info("---------- test_importer_retries_ok ----------")
    user_name = "retry_user"
    user_id_err = 12349  # this user id will fail in the mock twython client
    mock_client = tw_client_ok_retries(user_name, user_id_err=user_id_err)
    importer = FriendsImporter(mock_client, IMP_DATA_DIR, "good_csv.test_csv")
    importer.RETRY_SLEEP_CHECK_EVERY_SECS = 4
    importer.RETRY_SHORT_SECONDS_TO_WAIT = 6
    importer.RETRY_LONG_SECONDS_TO_WAIT = 10

    ok, msg, frnds_imported, frnds_remaining = importer.process()

    assert ok
    assert not msg
    assert len(frnds_imported) == 6
    assert not frnds_remaining
    logger.info("========== test_importer_retries_ok ============")


def test_importer_skipped_user_twitter_data_err(tw_client_skip):
    logger.info("---------- test_importer_skipped_user_twitter_data_err ----------")
    user_name = "importing_user"
    user_id_err = 12349  # this user id will fail in the mock twython client
    mock_client = tw_client_skip(user_name, user_id_err=user_id_err)
    importer = FriendsImporter(mock_client, IMP_DATA_DIR, "good_csv.test_csv")
    importer.RETRY_SLEEP_CHECK_EVERY_SECS = 4
    importer.RETRY_SHORT_SECONDS_TO_WAIT = 6
    importer.RETRY_LONG_SECONDS_TO_WAIT = 10

    ok, msg, frnds_imported, frnds_remaining = importer.process()

    assert ok
    assert not msg
    assert len(frnds_imported) == 5
    assert len(frnds_remaining) == 1
    assert frnds_remaining[0]['fr_id'] == user_id_err
    assert frnds_remaining[0]['reason_for_skipping'].find("could not be followed") >= 0
    logger.info("========== test_importer_skipped_user_twitter_data_err ============")


def test_importer_twitter_irrecoverable_err(tw_client_abort):
    logger.info("---------- test_importer_twitter_irrecoverable_err ----------")
    user_name = "erroring_user"
    user_id_err = 12349  # this user id will fail in the mock twython client
    mock_client = tw_client_abort(user_name, user_id_err=user_id_err)
    importer = FriendsImporter(mock_client, IMP_DATA_DIR, "good_csv.test_csv")
    importer.RETRY_SLEEP_CHECK_EVERY_SECS = 4
    importer.RETRY_SHORT_SECONDS_TO_WAIT = 6
    importer.RETRY_LONG_SECONDS_TO_WAIT = 10

    ok, msg, frnds_imported, frnds_remaining = importer.process()

    assert not ok
    assert msg.find("we added") >= 0
    assert len(frnds_imported) == 2
    assert len(frnds_remaining) == 4
    assert frnds_remaining[0]['fr_id'] == user_id_err
    logger.info("========== test_importer_twitter_irrecoverable_err ============")


# ---------------------
# private methods tests
# ---------------------

def test__parse_twithon_error_not_data_problem(tw_client_ok):
    logger.info("---------- test__parse_twithon_error_not_data_problem ----------")
    user_name = "not_data_user_error"
    err_msg = "Some twitter error"
    error_returned = TwythonError(msg=err_msg)
    mock_client = tw_client_ok(user_name)
    importer = FriendsImporter(mock_client, None, None)

    is_data_error, reason_for_skipping, irrecoverable_error = importer._parse_twithon_error(error_returned, user_name)

    assert not is_data_error
    assert not reason_for_skipping
    assert not irrecoverable_error
    logger.info("========== test__parse_twithon_error_not_data_problem ============")


def test__parse_twithon_error_irrecoverable_error(tw_client_ok):
    logger.info("---------- test__parse_twithon_error_irrecoverable_error ----------")
    user_name = "not_data_user_error"
    err_msg = "401 (Unauthorized), Invalid or expired token"
    error_returned = TwythonError(msg=err_msg)
    mock_client = tw_client_ok(user_name)
    importer = FriendsImporter(mock_client, None, None)

    is_data_error, reason_for_skipping, irrecoverable_error = importer._parse_twithon_error(error_returned, user_name)

    assert not is_data_error
    assert not reason_for_skipping
    assert irrecoverable_error
    logger.info("========== test__parse_twithon_error_irrecoverable_error ============")


def test__parse_twithon_error_user_not_found(tw_client_ok):
    logger.info("---------- test__parse_twithon_error_user_not_found ----------")
    user_name = "not_found_user_error"
    err_msg = "Cannot find specified user"
    error_returned = TwythonError(msg=err_msg)
    mock_client = tw_client_ok(user_name)
    importer = FriendsImporter(mock_client, None, None)

    is_data_error, reason_for_skipping, irrecoverable_error = importer._parse_twithon_error(error_returned, user_name)

    assert is_data_error
    assert reason_for_skipping
    assert not irrecoverable_error
    logger.info("========== test__parse_twithon_error_user_not_found ============")


def test__parse_twithon_error_user_blocked(tw_client_ok):
    logger.info("---------- test__parse_twithon_error_user_blocked ----------")
    user_name = "blocked_user_error"
    err_msg = "You have been blocked"
    error_returned = TwythonError(msg=err_msg)
    mock_client = tw_client_ok(user_name)
    importer = FriendsImporter(mock_client, None, None)

    is_data_error, reason_for_skipping, irrecoverable_error = importer._parse_twithon_error(error_returned, user_name)

    assert is_data_error
    assert reason_for_skipping
    assert not irrecoverable_error
    logger.info("========== test__parse_twithon_error_user_blocked ============")


def test__parse_twithon_error_account_protected(tw_client_ok):
    logger.info("---------- test__parse_twithon_error_account_protected ----------")
    user_name = "acc_protected_user_error"
    err_msg = "already requested to follow"
    error_returned = TwythonError(msg=err_msg)
    mock_client = tw_client_ok(user_name)
    importer = FriendsImporter(mock_client, None, None)

    is_data_error, reason_for_skipping, irrecoverable_error = importer._parse_twithon_error(error_returned, user_name)

    assert is_data_error
    assert reason_for_skipping
    assert not irrecoverable_error
    logger.info("========== test__parse_twithon_error_account_protected ============")

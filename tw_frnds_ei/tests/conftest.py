import pytest

from tw_frnds_ei.tests.mock_twython import MockTwython


# -----------------------
# Test fixtures
# -----------------------

@pytest.fixture()
def tw_client_ok():
    def _tw_client_ok(user_name, num_friends=None, data_pages=None):
        mc = MockTwython(user_name, MockTwython.SCENARIO_OK)
        mc.num_friends = num_friends
        mc.data_pages = data_pages
        return mc

    return _tw_client_ok


@pytest.fixture
def tw_client_ok_retries():
    def _tw_client_ok_retries(user_name, num_friends=None, data_pages=None, page_err=None, user_id_err=None):
        mc = MockTwython(user_name, MockTwython.SCENARIO_RETRY_OK)
        mc.num_friends = num_friends
        mc.data_pages = data_pages
        mc.page_err = page_err
        mc.user_id_err = user_id_err
        return mc

    return _tw_client_ok_retries


@pytest.fixture(params=[MockTwython.SCENARIO_RETRY_NOK, MockTwython.SCENARIO_NOK])
def tw_client_nok(request):
    def _tw_client_nok(user_name, num_friends=None, data_pages=None, page_err=None, user_id_err=None):
        mc = MockTwython(user_name, request.param)
        mc.num_friends = num_friends
        mc.data_pages = data_pages
        mc.page_err = page_err
        mc.user_id_err = user_id_err
        return mc

    return _tw_client_nok


@pytest.fixture(params=[MockTwython.SCENARIO_SKIP])
def tw_client_skip(request):
    def _tw_client_skip(user_name, num_friends=None, data_pages=None, page_err=None, user_id_err=None):
        mc = MockTwython(user_name, request.param)
        mc.num_friends = num_friends
        mc.data_pages = data_pages
        mc.page_err = page_err
        mc.user_id_err = user_id_err
        return mc

    return _tw_client_skip


@pytest.fixture(params=[MockTwython.SCENARIO_ABORT])
def tw_client_abort(request):
    def _tw_client_abort(user_name, num_friends=None, data_pages=None, page_err=None, user_id_err=None):
        mc = MockTwython(user_name, request.param)
        mc.num_friends = num_friends
        mc.data_pages = data_pages
        mc.page_err = page_err
        mc.user_id_err = user_id_err
        return mc

    return _tw_client_abort

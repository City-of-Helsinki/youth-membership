import pytest
from graphql_relay.node.node import to_global_id
from requests import HTTPError

from common_utils.oidc import TunnistamoTokenExchange
from common_utils.profile import ProfileAPI


def test_call_profile_api_and_fetch_my_profile(
    mocker, requests_mock, my_profile_response, settings
):
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_token", return_value="api_token"
    )
    requests_mock.post(settings.HELSINKI_PROFILE_API_URL, json=my_profile_response)
    api = ProfileAPI()

    profile = api.fetch_my_profile("auth_code")

    expected_data = {
        "id": to_global_id("ProfileNode", "5b36406d-da95-4cb0-88d8-2ec6f80e9fc9"),
    }
    assert profile == expected_data


def test_call_profile_api_fails(mocker, requests_mock, settings):
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_token", return_value="api_token"
    )
    requests_mock.post(settings.HELSINKI_PROFILE_API_URL, text="Nope", status_code=403)
    api = ProfileAPI()

    with pytest.raises(HTTPError):
        api.fetch_my_profile("auth_code")

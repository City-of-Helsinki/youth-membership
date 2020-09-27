import pytest
from requests import HTTPError

from common_utils.oidc import TunnistamoTokenExchange
from common_utils.profile import ProfileAPI

# ID in the mocked responses ProfileNode:5b36406d-da95-4cb0-88d8-2ec6f80e9fc9
PROFILE_ID = "UHJvZmlsZU5vZGU6NWIzNjQwNmQtZGE5NS00Y2IwLTg4ZDgtMmVjNmY4MGU5ZmM5"


def test_call_profile_api_and_fetch_my_profile(
    mocker, requests_mock, my_profile_response, settings
):
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_token", return_value="api_token"
    )
    requests_mock.post(settings.HELSINKI_PROFILE_API_URL, json=my_profile_response)
    api = ProfileAPI()

    profile = api.fetch_my_profile("auth_code")

    expected_data = {"id": PROFILE_ID}
    assert profile == expected_data


def test_call_profile_api_and_fetch_profile_with_id(
    mocker, requests_mock, profile_response, settings
):
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_token", return_value="api_token"
    )
    requests_mock.post(settings.HELSINKI_PROFILE_API_URL, json=profile_response)
    api = ProfileAPI()

    profile = api.fetch_profile("auth_code", PROFILE_ID)

    expected_data = {"id": PROFILE_ID}
    assert profile == expected_data


def test_call_profile_api_fails(mocker, requests_mock, settings):
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_token", return_value="api_token"
    )
    requests_mock.post(settings.HELSINKI_PROFILE_API_URL, text="Nope", status_code=403)
    api = ProfileAPI()

    with pytest.raises(HTTPError):
        api.fetch_my_profile("auth_code")

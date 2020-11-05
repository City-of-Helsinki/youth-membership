import datetime

import pytest
import pytz
from requests import HTTPError

from common_utils.profile import ProfileAPI

# ID in the mocked responses ProfileNode:5b36406d-da95-4cb0-88d8-2ec6f80e9fc9
PROFILE_ID = "UHJvZmlsZU5vZGU6NWIzNjQwNmQtZGE5NS00Y2IwLTg4ZDgtMmVjNmY4MGU5ZmM5"
FIRST_NAME = "Test"
LAST_NAME = "Person"


def test_call_profile_api_and_fetch_my_profile(
    requests_mock, my_profile_response, settings
):
    requests_mock.post(settings.HELSINKI_PROFILE_API_URL, json=my_profile_response)
    api = ProfileAPI()

    profile = api.fetch_my_profile("api_token")

    expected_data = {
        "id": PROFILE_ID,
        "first_name": FIRST_NAME,
        "last_name": LAST_NAME,
    }
    assert profile == expected_data


def test_call_profile_api_and_fetch_profile_with_id(
    requests_mock, profile_response, settings
):
    requests_mock.post(settings.HELSINKI_PROFILE_API_URL, json=profile_response)
    api = ProfileAPI()

    profile = api.fetch_profile("api_token", PROFILE_ID)

    expected_data = {"id": PROFILE_ID}
    assert profile == expected_data


def test_call_profile_api_fails(requests_mock, settings):
    requests_mock.post(settings.HELSINKI_PROFILE_API_URL, text="Nope", status_code=403)
    api = ProfileAPI()

    with pytest.raises(HTTPError):
        api.fetch_my_profile("api_token")


def test_create_my_profile_temporary_read_access_token(
    requests_mock, settings, temporary_token_response
):
    requests_mock.post(settings.HELSINKI_PROFILE_API_URL, json=temporary_token_response)

    token = "a2fe1f2b-c9fe-4329-a270-400fa0dfd9f5"
    expires_at = datetime.datetime(2020, 10, 24, 9, 46, 52, 0, pytz.UTC)

    api = ProfileAPI()

    profile = api.create_temporary_access_token("api_token")

    expected_data = {"token": token, "expires_at": expires_at}
    assert profile == expected_data

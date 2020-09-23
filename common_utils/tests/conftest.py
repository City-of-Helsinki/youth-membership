import pytest

from common_utils.utils import read_json_file


@pytest.fixture(autouse=True)
def setup_helsinki_profile_settings(settings):
    settings.HELSINKI_PROFILE_API_URL = "http://localhost"


@pytest.fixture(scope="session")
def my_profile_response():
    return read_json_file(__file__, "responses", "my_profile_response.json")

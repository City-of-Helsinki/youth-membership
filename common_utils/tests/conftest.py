import pytest

from common_utils.utils import read_json_file
from youth_membership.tests.conftest import *  # noqa


@pytest.fixture(scope="session")
def my_profile_response():
    return read_json_file(__file__, "responses", "my_profile_response.json")


@pytest.fixture(scope="session")
def profile_response():
    return read_json_file(__file__, "responses", "profile_response.json")

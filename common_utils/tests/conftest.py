import pytest

from common_utils.utils import read_json_file
from youth_membership.tests.conftest import *  # noqa


@pytest.fixture(scope="session")
def my_profile_response():
    """ProfileNode:5b36406d-da95-4cb0-88d8-2ec6f80e9fc9"""
    return read_json_file(__file__, "responses", "my_profile_response.json")


@pytest.fixture(scope="session")
def profile_response():
    """ProfileNode:5b36406d-da95-4cb0-88d8-2ec6f80e9fc9"""
    return read_json_file(__file__, "responses", "profile_response.json")


@pytest.fixture(scope="session")
def temporary_token_response():
    return read_json_file(__file__, "responses", "temporary_token_response.json")


@pytest.fixture(scope="session")
def profile_access_token_response():
    """RestrictedProfileNode:5b36406d-da95-4cb0-88d8-2ec6f80e9fc9"""
    return read_json_file(__file__, "responses", "profile_access_token_response.json")

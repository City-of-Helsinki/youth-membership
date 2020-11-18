import pytest
from rest_framework.test import APIClient

from youth_membership.tests.conftest import *  # noqa
from youths.tests.factories import (
    MyProfileAPIResponse,
    ProfileAPIResponse,
    ProfileAPITokenResponse,
    RestrictedProfileAPIResponse,
    YouthProfileFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def youth_profile():
    return YouthProfileFactory()


@pytest.fixture(autouse=True)
def setup_youth_membership_dates(settings):
    settings.YOUTH_MEMBERSHIP_SEASON_END_DATE = 31, 8
    settings.YOUTH_MEMBERSHIP_FULL_SEASON_START_MONTH = 5


@pytest.fixture(autouse=True)
def setup_gdpr_api(settings):
    settings.GDPR_API_ENABLED = True


@pytest.fixture
def profile_api_response():
    return ProfileAPIResponse()


@pytest.fixture
def my_profile_api_response():
    return MyProfileAPIResponse()


@pytest.fixture
def token_response():
    return ProfileAPITokenResponse()


@pytest.fixture
def restricted_profile_response():
    return RestrictedProfileAPIResponse()

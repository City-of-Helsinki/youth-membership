import factory.random
import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from graphene.test import Client as GraphQLClient

from common_utils.views import SentryGraphQLView
from users.factories import GroupFactory, SuperuserFactory, UserFactory
from youth_membership.schema import schema


@pytest.fixture(autouse=True)
def autouse_db(db):
    pass


@pytest.fixture(autouse=True)
def setup_helsinki_profile_settings(settings):
    settings.HELSINKI_PROFILE_API_URL = "https://localhost"


@pytest.fixture(autouse=True)
def set_random_seed():
    factory.random.reseed_random(666)


@pytest.fixture(autouse=True)
def email_setup(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def anon_user():
    return AnonymousUser()


@pytest.fixture
def superuser():
    return SuperuserFactory()


@pytest.fixture
def staff_group():
    return GroupFactory(name=settings.YOUTH_MEMBERSHIP_STAFF_GROUP)


@pytest.fixture
def staff_user(staff_group):
    user = UserFactory()
    user.groups.add(staff_group)
    return user


def get_gql_client_with_error_formating():
    return GraphQLClient(schema, format_error=SentryGraphQLView.format_error)


@pytest.fixture
def gql_client():
    gql_client = get_gql_client_with_error_formating()
    return gql_client


@pytest.fixture
def anon_user_gql_client(anon_user):
    gql_client = get_gql_client_with_error_formating()
    gql_client.user = anon_user
    return gql_client


@pytest.fixture
def user_gql_client(user):
    gql_client = get_gql_client_with_error_formating()
    gql_client.user = user
    return gql_client


@pytest.fixture
def staff_user_gql_client(staff_user):
    gql_client = get_gql_client_with_error_formating()
    gql_client.user = staff_user
    return gql_client


@pytest.fixture
def superuser_gql_client(superuser):
    gql_client = get_gql_client_with_error_formating()
    gql_client.user = superuser
    return gql_client

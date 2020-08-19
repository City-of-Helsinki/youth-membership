import uuid
from datetime import date
from string import Template

import pytest
from django.utils import timezone
from freezegun import freeze_time
from graphql_relay.node.node import to_global_id

from common_utils.consts import PERMISSION_DENIED_ERROR
from youths.tests.factories import YouthProfileFactory


# TODO Check properly
def test_anon_user_query_should_fail(rf, youth_profile, anon_user_gql_client):
    request = rf.post("/graphql")
    request.user = anon_user_gql_client.user

    t = Template(
        """
        {
            youthProfile(profileId: "${profileId}") {
                schoolClass
            }
        }
        """
    )
    query = t.substitute(profileId=uuid.uuid4())
    expected_data = {"youthProfile": None}
    executed = anon_user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_query_by_id_should_fail(rf, youth_profile, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            youthProfile(profileId: "${profileId}") {
                schoolClass
            }
        }
        """
    )
    query = t.substitute(profileId=uuid.uuid4())
    expected_data = {"youthProfile": None}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data
    assert (
        executed["errors"][0].get("extensions").get("code") == PERMISSION_DENIED_ERROR
    )


def test_normal_user_can_query_own_youth_profile(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    youth_profile = YouthProfileFactory(user=user_gql_client.user)

    query = """
        {
            youthProfile {
                id
                schoolClass
                membershipNumber
            }
        }
    """
    expected_data = {
        "youthProfile": {
            # TODO Change this to global id ?
            "id": str(youth_profile.pk),
            "schoolClass": youth_profile.school_class,
            "membershipNumber": youth_profile.membership_number,
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


# Parametrize superuser + staff user
@pytest.mark.parametrize(
    "gql_client",
    [
        pytest.lazy_fixture("superuser_gql_client"),
        pytest.lazy_fixture("staff_user_gql_client"),
    ],
)
def test_staff_user_can_query_by_id(rf, youth_profile, gql_client):
    request = rf.post("/graphql")
    request.user = gql_client.user

    t = Template(
        """
        {
            youthProfile(profileId: "${profileId}") {
                id
                schoolClass
            }
        }
        """
    )
    query = t.substitute(
        profileId=to_global_id(type="YouthProfileType", id=youth_profile.pk)
    )
    expected_data = {
        "youthProfile": {
            # TODO Change this to global id ?
            "id": str(youth_profile.pk),
            "schoolClass": youth_profile.school_class,
        }
    }
    executed = gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_anon_user_query_with_token(rf, youth_profile, anon_user_gql_client):
    request = rf.post("/graphql")
    request.user = anon_user_gql_client.user

    t = Template(
        """
        {
            youthProfileByApprovalToken(token: "${approvalToken}") {
                schoolClass
            }
        }
        """
    )
    query = t.substitute(approvalToken=youth_profile.approval_token)
    expected_data = {
        "youthProfileByApprovalToken": {"schoolClass": youth_profile.school_class}
    }
    executed = anon_user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_youth_profile_should_show_correct_membership_status(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    youth_profile = YouthProfileFactory(user=user_gql_client.user)

    query = """
        {
            youthProfile {
                membershipStatus
            }
        }
    """
    expected_data = {"youthProfile": {"membershipStatus": "PENDING"}}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    youth_profile.approved_time = timezone.now()
    youth_profile.save()
    expected_data = {"youthProfile": {"membershipStatus": "ACTIVE"}}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    youth_profile.expiration = date.today()
    youth_profile.save()
    expected_data = {"youthProfile": {"membershipStatus": "EXPIRED"}}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    query = """
        {
            youthProfile {
                membershipStatus
                renewable
            }
        }
    """

    with freeze_time("2020-05-01"):
        youth_profile.expiration = date(2020, 8, 31)
        youth_profile.approved_time = date(2019, 8, 1)
        youth_profile.save()
        expected_data = {
            "youthProfile": {"membershipStatus": "ACTIVE", "renewable": True}
        }
        executed = user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data

    with freeze_time("2020-09-01"):
        youth_profile.expiration = date(2021, 8, 31)
        youth_profile.approved_time = date(2020, 4, 30)
        youth_profile.save()
        expected_data = {
            "youthProfile": {"membershipStatus": "EXPIRED", "renewable": False}
        }
        executed = user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data

        youth_profile.approved_time = timezone.datetime(2020, 1, 1)
        youth_profile.expiration = date(2021, 8, 31)
        youth_profile.save()
        expected_data = {
            "youthProfile": {"membershipStatus": "RENEWING", "renewable": False}
        }
        with freeze_time("2020-05-01"):
            executed = user_gql_client.execute(query, context=request)
            assert dict(executed["data"]) == expected_data
        with freeze_time("2020-08-31"):
            executed = user_gql_client.execute(query, context=request)
            assert dict(executed["data"]) == expected_data

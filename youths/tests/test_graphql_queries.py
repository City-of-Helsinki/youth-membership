import uuid
from datetime import date
from string import Template

import pytest
from django.utils import timezone
from freezegun import freeze_time
from graphql_relay.node.node import to_global_id

from common_utils.consts import PERMISSION_DENIED_ERROR
from youths.tests.factories import YouthProfileFactory


@pytest.mark.parametrize("use_proper_profile_id", [True, False])
def test_anon_user_query_should_fail(
    rf, youth_profile, anon_user_gql_client, use_proper_profile_id
):
    request = rf.post("/graphql")
    request.user = anon_user_gql_client.user

    t = Template(
        """
        {
            youthProfile(id: "${id}") {
                schoolClass
            }
        }
        """
    )
    if use_proper_profile_id:
        query = t.substitute(
            id=to_global_id(type="YouthProfileNode", id=youth_profile.pk)
        )
    else:
        query = t.substitute(id=to_global_id(type="YouthProfileNode", id=uuid.uuid4()))
    expected_data = {"youthProfile": None}
    executed = anon_user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data
    assert (
        executed["errors"][0].get("extensions").get("code") == PERMISSION_DENIED_ERROR
    )


@pytest.mark.parametrize(
    "gql_client",
    [
        pytest.lazy_fixture("user_gql_client"),
        pytest.lazy_fixture("staff_user_gql_client"),
        pytest.lazy_fixture("superuser_gql_client"),
    ],
)
def test_querying_non_existant_profile_returns_none(rf, gql_client):
    request = rf.post("/graphql")
    request.user = gql_client.user

    t = Template(
        """
        {
            youthProfile(id: "${id}") {
                schoolClass
            }
        }
        """
    )
    query = t.substitute(id=to_global_id(type="YouthProfileNode", id=uuid.uuid4()))
    expected_data = {"youthProfile": None}
    executed = gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_own_youth_profile_by_id(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    youth_profile = YouthProfileFactory(user=user_gql_client.user)
    profile_id = to_global_id(type="YouthProfileNode", id=youth_profile.pk)
    t = Template(
        """
        {
            youthProfile(id: "${id}") {
                id
                schoolClass
                membershipNumber
            }
        }
        """
    )
    query = t.substitute(id=profile_id)
    expected_data = {
        "youthProfile": {
            "id": profile_id,
            "schoolClass": youth_profile.school_class,
            "membershipNumber": youth_profile.membership_number,
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_cannot_query_someone_elses_youth_profile_by_id(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    youth_profile = YouthProfileFactory()
    profile_id = to_global_id(type="YouthProfileNode", id=youth_profile.pk)

    t = Template(
        """
        {
            youthProfile(id: "${id}") {
                id
                schoolClass
                membershipNumber
            }
        }
        """
    )
    query = t.substitute(id=profile_id)
    expected_data = {"youthProfile": None}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_my_youth_profile(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    youth_profile = YouthProfileFactory(user=user_gql_client.user)

    query = """
        {
            myYouthProfile {
                id
                schoolClass
                membershipNumber
            }
        }
    """
    expected_data = {
        "myYouthProfile": {
            "id": to_global_id(type="YouthProfileNode", id=youth_profile.pk),
            "schoolClass": youth_profile.school_class,
            "membershipNumber": youth_profile.membership_number,
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


@pytest.mark.parametrize(
    "gql_client",
    [
        pytest.lazy_fixture("superuser_gql_client"),
        pytest.lazy_fixture("staff_user_gql_client"),
    ],
)
def test_staff_user_can_query_own_youth_profile_by_id(rf, youth_profile, gql_client):
    request = rf.post("/graphql")
    request.user = gql_client.user
    profile_id = to_global_id(type="YouthProfileNode", id=youth_profile.pk)

    t = Template(
        """
        {
            youthProfile(id: "${id}") {
                id
                schoolClass
            }
        }
        """
    )
    query = t.substitute(id=profile_id)
    expected_data = {
        "youthProfile": {"id": profile_id, "schoolClass": youth_profile.school_class}
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
            myYouthProfile {
                membershipStatus
            }
        }
    """
    expected_data = {"myYouthProfile": {"membershipStatus": "PENDING"}}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    youth_profile.set_approved()
    youth_profile.save()
    expected_data = {"myYouthProfile": {"membershipStatus": "ACTIVE"}}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    youth_profile.expiration = date.today()
    youth_profile.save()
    expected_data = {"myYouthProfile": {"membershipStatus": "EXPIRED"}}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    query = """
        {
            myYouthProfile {
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
            "myYouthProfile": {"membershipStatus": "ACTIVE", "renewable": True}
        }
        executed = user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data

    with freeze_time("2020-09-01"):
        youth_profile.expiration = date(2021, 8, 31)
        youth_profile.approved_time = date(2020, 4, 30)
        youth_profile.save()
        expected_data = {
            "myYouthProfile": {"membershipStatus": "EXPIRED", "renewable": False}
        }
        executed = user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data

        youth_profile.approved_time = timezone.datetime(2020, 1, 1)
        youth_profile.expiration = date(2021, 8, 31)
        youth_profile.save()
        expected_data = {
            "myYouthProfile": {"membershipStatus": "RENEWING", "renewable": False}
        }
        with freeze_time("2020-05-01"):
            executed = user_gql_client.execute(query, context=request)
            assert dict(executed["data"]) == expected_data
        with freeze_time("2020-08-31"):
            executed = user_gql_client.execute(query, context=request)
            assert dict(executed["data"]) == expected_data


@pytest.mark.parametrize(
    "gql_client",
    [
        pytest.lazy_fixture("anon_user_gql_client"),
        pytest.lazy_fixture("user_gql_client"),
    ],
)
def test_normal_user_cannot_query_all_youth_profiles(rf, gql_client):
    request = rf.post("/graphql")
    request.user = gql_client.user
    YouthProfileFactory.create_batch(2)

    query = """
        query {
            youthProfiles {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """
    executed = gql_client.execute(query, context=request)

    expected_data = {"youthProfiles": None}
    assert dict(executed["data"]) == expected_data
    assert (
        executed["errors"][0].get("extensions").get("code") == PERMISSION_DENIED_ERROR
    )


def test_staff_user_can_query_all_youth_profiles(rf, staff_user_gql_client):
    request = rf.post("/graphql")
    request.user = staff_user_gql_client.user
    YouthProfileFactory.create_batch(2)

    query = """
        query {
            youthProfiles {
                totalCount
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    executed = staff_user_gql_client.execute(query, context=request)
    assert executed["data"]["youthProfiles"]["totalCount"] == 2


def test_staff_user_can_filter_all_youth_profiles(rf, staff_user_gql_client):
    request = rf.post("/graphql")
    YouthProfileFactory.create_batch(2)
    youth_profile = YouthProfileFactory()
    request.user = staff_user_gql_client.user

    t = Template(
        """
        query {
            youthProfiles(membershipNumber:"${number}") {
                totalCount
                count
                edges {
                    node {
                        id
                        membershipNumber

                    }
                }
            }
        }
        """
    )
    query = t.substitute(number=youth_profile.membership_number)
    executed = staff_user_gql_client.execute(query, context=request)
    assert executed["data"]["youthProfiles"]["totalCount"] == 3
    assert executed["data"]["youthProfiles"]["count"] == 1

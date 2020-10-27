from datetime import date, datetime, timedelta
from string import Template

import pytest
from freezegun import freeze_time
from graphql_relay.node.node import from_global_id, to_global_id

from common_utils.consts import PERMISSION_DENIED_ERROR, PROFILE_DOES_NOT_EXIST_ERROR
from common_utils.profile import ProfileAPI
from youths.consts import (
    APPROVER_EMAIL_CANNOT_BE_EMPTY_FOR_MINORS_ERROR,
    CANNOT_CREATE_YOUTH_PROFILE_IF_UNDER_13_YEARS_OLD_ERROR,
    CANNOT_RENEW_YOUTH_PROFILE_ERROR,
    CANNOT_SET_PHOTO_USAGE_PERMISSION_IF_UNDER_15_YEARS_ERROR,
)
from youths.enums import YouthLanguage
from youths.models import YouthProfile
from youths.tests.factories import YouthProfileFactory


def test_normal_user_can_create_youth_profile_mutation(
    rf, user_gql_client, mocker, profile_api_response, token_response
):
    mocker.patch.object(
        ProfileAPI, "fetch_my_profile", return_value=profile_api_response
    )
    mocker.patch.object(
        ProfileAPI, "create_temporary_access_token", return_value=token_response
    )
    profile_id = from_global_id(profile_api_response["id"])[1]

    request = rf.post("/graphql")
    request.user = user_gql_client.user
    t = Template(
        """
        mutation{
            createMyYouthProfile(
                input: {
                    youthProfile: {
                        schoolClass: "${schoolClass}"
                        schoolName: "${schoolName}"
                        languageAtHome: ${language}
                        approverEmail: "${approverEmail}"
                        birthDate: "${birthDate}"
                    }
                    profileApiToken: "token"
                }
            )
            {
                youthProfile {
                    id
                    schoolClass
                    schoolName
                    approverEmail
                    birthDate
                }
            }
        }
        """
    )
    creation_data = {
        "schoolClass": "2A",
        "schoolName": "Alakoulu",
        "approverEmail": "hyvaksyja@example.com",
        "language": YouthLanguage.FINNISH.name,
        "birthDate": "2004-04-11",
    }
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            # id is fetched from Profile API
            "id": to_global_id(type="YouthProfileNode", id=profile_id),
            "schoolClass": creation_data["schoolClass"],
            "schoolName": creation_data["schoolName"],
            "approverEmail": creation_data["approverEmail"],
            "birthDate": creation_data["birthDate"],
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["createMyYouthProfile"]) == expected_data


def test_profile_access_token_is_saved_when_using_create_my_youth_profile(
    rf, user_gql_client, mocker, profile_api_response, token_response
):
    """Temporary profile access token can be used later when access to profile information
    is needed e.g. when unauthenticated parent approves the youth membership."""
    mocker.patch.object(
        ProfileAPI, "fetch_my_profile", return_value=profile_api_response
    )
    mocker.patch.object(
        ProfileAPI, "create_temporary_access_token", return_value=token_response
    )
    profile_id = from_global_id(profile_api_response["id"])[1]

    request = rf.post("/graphql")
    request.user = user_gql_client.user
    t = Template(
        """
        mutation {
            createMyYouthProfile (
                input: {
                    youthProfile: {
                        schoolClass: "${schoolClass}"
                        schoolName: "${schoolName}"
                        languageAtHome: ${language}
                        approverEmail: "${approverEmail}"
                        birthDate: "${birthDate}"
                    }
                    profileApiToken: "token"
                }
            )
            {
                youthProfile {
                    id
                }
            }
        }
        """
    )
    creation_data = {
        "schoolClass": "2A",
        "schoolName": "Alakoulu",
        "approverEmail": "hyvaksyja@example.com",
        "language": YouthLanguage.FINNISH.name,
        "birthDate": "2004-04-11",
    }
    query = t.substitute(**creation_data)

    user_gql_client.execute(query, context=request)

    youth_profile = YouthProfile.objects.get(pk=profile_id)
    assert youth_profile.profile_access_token == token_response["token"]
    assert youth_profile.profile_access_token_expiration == token_response["expires_at"]


def test_normal_user_over_18_years_old_can_create_approved_youth_profile_mutation(
    rf, user_gql_client, mocker, profile_api_response, token_response
):
    mocker.patch.object(
        ProfileAPI, "fetch_my_profile", return_value=profile_api_response
    )
    mocker.patch.object(
        ProfileAPI, "create_temporary_access_token", return_value=token_response
    )
    profile_id = from_global_id(profile_api_response["id"])[1]

    request = rf.post("/graphql")
    request.user = user_gql_client.user
    today = date.today()

    t = Template(
        """
        mutation{
            createMyYouthProfile(
                input: {
                    youthProfile: {
                        schoolClass: "${schoolClass}"
                        schoolName: "${schoolName}"
                        birthDate: "${birthDate}"
                    }
                    profileApiToken: "token"
                }
            )
            {
                youthProfile {
                    id
                    schoolClass
                    schoolName
                    birthDate
                    membershipStatus
                }
            }
        }
        """
    )
    birth_date = today.replace(year=today.year - 18) - timedelta(days=1)
    creation_data = {
        "schoolClass": "2A",
        "schoolName": "Alakoulu",
        "birthDate": birth_date.strftime("%Y-%m-%d"),
    }
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            "id": to_global_id(type="YouthProfileNode", id=profile_id),
            "schoolClass": creation_data["schoolClass"],
            "schoolName": creation_data["schoolName"],
            "birthDate": creation_data["birthDate"],
            "membershipStatus": "ACTIVE",
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["createMyYouthProfile"]) == expected_data


def test_user_cannot_create_youth_profile_without_approver_email_field_if_under_18_years_old(
    rf, user_gql_client, mocker, profile_api_response
):
    mocker.patch.object(
        ProfileAPI, "fetch_my_profile", return_value=profile_api_response
    )
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    today = date.today()

    t = Template(
        """
        mutation{
            createMyYouthProfile(
                input: {
                    youthProfile: {
                        birthDate: "${birthDate}"
                    }
                    profileApiToken: "token"
                }
            )
            {
                youthProfile {
                    birthDate
                }
            }
        }
        """
    )
    birth_date = today.replace(year=today.year - 18) + timedelta(days=1)
    creation_data = {
        "birthDate": birth_date.strftime("%Y-%m-%d"),
    }
    query = t.substitute(**creation_data)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert (
        executed["errors"][0]["extensions"]["code"]
        == APPROVER_EMAIL_CANNOT_BE_EMPTY_FOR_MINORS_ERROR
    )


def test_user_cannot_create_youth_profile_if_under_13_years_old(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    today = date.today()

    t = Template(
        """
        mutation{
            createMyYouthProfile(
                input: {
                    youthProfile: {
                        schoolClass: "${schoolClass}"
                        schoolName: "${schoolName}"
                        languageAtHome: ${language}
                        approverEmail: "${approverEmail}"
                        birthDate: "${birthDate}"
                    }
                    profileApiToken: "token"
                }
            )
            {
                youthProfile {
                    schoolClass
                    schoolName
                    approverEmail
                    birthDate
                }
            }
        }
        """
    )
    birth_date = today.replace(year=today.year - 13) + timedelta(days=1)
    creation_data = {
        "schoolClass": "2A",
        "schoolName": "Alakoulu",
        "approverEmail": "hyvaksyja@ex.com",
        "language": YouthLanguage.FINNISH.name,
        "birthDate": birth_date.strftime("%Y-%m-%d"),
    }
    query = t.substitute(**creation_data)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert (
        executed["errors"][0]["extensions"]["code"]
        == CANNOT_CREATE_YOUTH_PROFILE_IF_UNDER_13_YEARS_OLD_ERROR
    )


def test_user_can_create_youth_profile_with_photo_usage_field_if_over_15_years_old(
    rf, user_gql_client, mocker, profile_api_response, token_response
):
    mocker.patch.object(
        ProfileAPI, "fetch_my_profile", return_value=profile_api_response
    )
    mocker.patch.object(
        ProfileAPI, "create_temporary_access_token", return_value=token_response
    )
    profile_id = from_global_id(profile_api_response["id"])[1]

    request = rf.post("/graphql")
    request.user = user_gql_client.user
    today = date.today()

    t = Template(
        """
        mutation{
            createMyYouthProfile(
                input: {
                    youthProfile: {
                        photoUsageApproved: ${photoUsageApproved}
                        approverEmail: "${approverEmail}"
                        birthDate: "${birthDate}"
                    }
                    profileApiToken: "token"
                }
            )
            {
                youthProfile {
                    id
                    photoUsageApproved
                    approverEmail
                    birthDate
                }
            }
        }
        """
    )
    birth_date = today.replace(year=today.year - 15) - timedelta(days=1)
    creation_data = {
        "approverEmail": "hyvaksyja@ex.com",
        "photoUsageApproved": "true",
        "birthDate": birth_date.strftime("%Y-%m-%d"),
    }
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            "id": to_global_id(type="YouthProfileNode", id=profile_id),
            "photoUsageApproved": True,
            "approverEmail": creation_data["approverEmail"],
            "birthDate": creation_data["birthDate"],
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["createMyYouthProfile"]) == expected_data


def test_user_cannot_create_youth_profile_with_photo_usage_field_if_under_15_years_old(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    today = date.today()

    t = Template(
        """
        mutation{
            createMyYouthProfile(
                input: {
                    youthProfile: {
                        photoUsageApproved: ${photoUsageApproved}
                        approverEmail: "${approverEmail}"
                        birthDate: "${birthDate}"
                    }
                    profileApiToken: "token"
                }
            )
            {
                youthProfile {
                    photoUsageApproved
                    approverEmail
                    birthDate
                }
            }
        }
        """
    )
    birth_date = today.replace(year=today.year - 15) + timedelta(days=1)
    creation_data = {
        "approverEmail": "hyvaksyja@ex.com",
        "photoUsageApproved": "true",
        "birthDate": birth_date.strftime("%Y-%m-%d"),
    }
    query = t.substitute(**creation_data)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert (
        executed["errors"][0]["extensions"]["code"]
        == CANNOT_SET_PHOTO_USAGE_PERMISSION_IF_UNDER_15_YEARS_ERROR
    )


def test_normal_user_can_update_youth_profile_mutation(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    youth_profile = YouthProfileFactory(user=user_gql_client.user)

    t = Template(
        """
        mutation{
            updateMyYouthProfile(
                input: {
                    youthProfile: {
                        schoolClass: "${schoolClass}"
                        birthDate: "${birthDate}"
                    }
                }
            )
            {
                youthProfile {
                    schoolClass
                    schoolName
                    birthDate
                }
            }
        }
        """
    )
    creation_data = {"schoolClass": "2A", "birthDate": "2002-02-02"}
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            "schoolClass": creation_data["schoolClass"],
            "schoolName": youth_profile.school_name,
            "birthDate": creation_data["birthDate"],
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["updateMyYouthProfile"]) == expected_data


def test_user_can_update_youth_profile_with_photo_usage_field_if_over_15_years_old(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    YouthProfileFactory(user=user_gql_client.user)
    today = date.today()

    t = Template(
        """
        mutation{
            updateMyYouthProfile(
                input: {
                    youthProfile: {
                        photoUsageApproved: ${photoUsageApproved}
                        birthDate: "${birthDate}"
                    }
                }
            )
            {
                youthProfile {
                    photoUsageApproved
                    birthDate
                }
            }
        }
        """
    )
    birth_date = today.replace(year=today.year - 15) - timedelta(days=1)
    creation_data = {
        "photoUsageApproved": "true",
        "birthDate": birth_date.strftime("%Y-%m-%d"),
    }
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            "photoUsageApproved": True,
            "birthDate": creation_data["birthDate"],
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["updateMyYouthProfile"]) == expected_data


def test_user_cannot_update_youth_profile_with_photo_usage_field_if_under_15_years_old(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    YouthProfileFactory(user=user_gql_client.user)
    today = date.today()

    t = Template(
        """
        mutation{
            updateMyYouthProfile(
                input: {
                    youthProfile: {
                        photoUsageApproved: ${photoUsageApproved}
                        birthDate: "${birthDate}"
                    }
                }
            )
            {
                youthProfile {
                    photoUsageApproved
                    birthDate
                }
            }
        }
        """
    )
    birth_date = today.replace(year=today.year - 15) + timedelta(days=1)
    creation_data = {
        "photoUsageApproved": "true",
        "birthDate": birth_date.strftime("%Y-%m-%d"),
    }
    query = t.substitute(**creation_data)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert (
        executed["errors"][0]["extensions"]["code"]
        == CANNOT_SET_PHOTO_USAGE_PERMISSION_IF_UNDER_15_YEARS_ERROR
    )


def test_user_can_update_youth_profile_with_photo_usage_field_if_over_15_years_old_based_on_existing_birth_date(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    today = date.today()
    birth_date = today.replace(year=today.year - 15) - timedelta(days=1)
    YouthProfileFactory(user=user_gql_client.user, birth_date=birth_date)

    t = Template(
        """
        mutation{
            updateMyYouthProfile(
                input: {
                    youthProfile: {
                        photoUsageApproved: ${photoUsageApproved}
                    }
                }
            )
            {
                youthProfile {
                    photoUsageApproved
                }
            }
        }
        """
    )
    creation_data = {"photoUsageApproved": "true"}
    query = t.substitute(**creation_data)
    expected_data = {"youthProfile": {"photoUsageApproved": True}}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["updateMyYouthProfile"]) == expected_data


def test_user_cannot_update_youth_profile_with_photo_usage_field_if_under_15_years_old_based_on_existing_birth_date(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    today = date.today()
    birth_date = today.replace(year=today.year - 15) + timedelta(days=1)
    YouthProfileFactory(user=user_gql_client.user, birth_date=birth_date)

    t = Template(
        """
        mutation{
            updateMyYouthProfile(
                input: {
                    youthProfile: {
                        photoUsageApproved: ${photoUsageApproved}
                    }
                }
            )
            {
                youthProfile {
                    photoUsageApproved
                }
            }
        }
        """
    )
    creation_data = {"photoUsageApproved": "true"}
    query = t.substitute(**creation_data)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert (
        executed["errors"][0]["extensions"]["code"]
        == CANNOT_SET_PHOTO_USAGE_PERMISSION_IF_UNDER_15_YEARS_ERROR
    )


def test_staff_user_can_update_youth_profile_with_photo_usage_field_if_under_15_years_old(
    rf, staff_user_gql_client
):
    user = staff_user_gql_client.user
    request = rf.post("/graphql")
    request.user = user

    # Under 15 years
    today = date.today()
    birth_date = today.replace(year=today.year - 15) + timedelta(days=1)
    youth_profile = YouthProfileFactory(birth_date=birth_date)

    t = Template(
        """
        mutation {
            updateYouthProfile(input:{
                id: \"${id}\",
                youthProfile: {
                    photoUsageApproved: ${photo_usage_approved}
                }
            }) {
                youthProfile {
                    photoUsageApproved
                }
            }
        }
    """
    )
    mutation = t.substitute(
        id=to_global_id(type="YouthProfileNode", id=youth_profile.pk),
        photo_usage_approved="true",
    )
    executed = staff_user_gql_client.execute(mutation, context=request)

    expected_data = {"youthProfile": {"photoUsageApproved": True}}
    youth_profile.refresh_from_db()
    assert "errors" not in executed
    assert youth_profile.photo_usage_approved
    assert dict(executed["data"]["updateYouthProfile"]) == expected_data


def test_anon_user_can_approve_with_token(rf, anon_user_gql_client, youth_profile):
    request = rf.post("/graphql")
    request.user = anon_user_gql_client.user

    t = Template(
        """
        mutation{
            approveYouthProfile(
                input: {
                    approvalToken: "${token}",
                    approvalData: {
                        photoUsageApproved: true
                        approverFirstName: "${approver_first_name}"
                        approverLastName: "${approver_last_name}"
                        approverPhone: "${approver_phone}"
                        approverEmail: "${approver_email}"
                        birthDate: "${birthDate}"
                    }
                }
            )
            {
                youthProfile {
                    photoUsageApproved
                    approverFirstName
                    approverLastName
                    approverPhone
                    approverEmail
                    birthDate
                }
            }
        }
        """
    )
    approval_data = {
        "token": youth_profile.approval_token,
        "approver_first_name": "Teppo",
        "approver_last_name": "Testi",
        "approver_phone": "0401234567",
        "approver_email": "teppo@testi.com",
        "birthDate": "2002-02-02",
    }
    query = t.substitute(**approval_data)
    expected_data = {
        "youthProfile": {
            "photoUsageApproved": True,
            "approverFirstName": approval_data["approver_first_name"],
            "approverLastName": approval_data["approver_last_name"],
            "approverPhone": approval_data["approver_phone"],
            "approverEmail": approval_data["approver_email"],
            "birthDate": approval_data["birthDate"],
        }
    }
    executed = anon_user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["approveYouthProfile"]) == expected_data


@pytest.mark.skip(reason="Need to implement a way to get email from profile")
def test_missing_primary_email_error(rf, youth_profile, anon_user_gql_client):
    request = rf.post("/graphql")
    request.user = anon_user_gql_client.user

    t = Template(
        """
        mutation{
            approveYouthProfile(
                input: {
                    approvalToken: "${token}",
                    approvalData: {
                        photoUsageApproved: true
                        approverFirstName: "${approver_first_name}"
                        approverLastName: "${approver_last_name}"
                        approverPhone: "${approver_phone}"
                        approverEmail: "${approver_email}"
                        birthDate: "${birthDate}"
                    }
                }
            )
            {
                youthProfile {
                    photoUsageApproved
                    approverFirstName
                    approverLastName
                    approverPhone
                    approverEmail
                    birthDate
                }
            }
        }
        """
    )
    approval_data = {
        "token": youth_profile.approval_token,
        "approver_first_name": "Teppo",
        "approver_last_name": "Testi",
        "approver_phone": "0401234567",
        "approver_email": "teppo@testi.com",
        "birthDate": "2002-02-02",
    }
    query = t.substitute(**approval_data)
    executed = anon_user_gql_client.execute(query, context=request)

    assert (
        executed["errors"][0].get("extensions").get("code")
        == "PROFILE_HAS_NO_PRIMARY_EMAIL_ERROR"
    )


def test_youth_profile_expiration_should_renew_and_be_approvable(
    rf, user_gql_client, anon_user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    # Let's create a youth profile in the 2020
    with freeze_time("2020-05-02"):
        today = date.today()
        youth_profile = YouthProfileFactory(
            user=user_gql_client.user,
            approved_time=datetime.today(),
            birth_date=today.replace(year=today.year - 15),
        )

    # In the year 2021, let's renew it
    with freeze_time("2021-05-01"):
        mutation = """
            mutation {
                renewMyYouthProfile(input:{}) {
                    youthProfile {
                        membershipStatus
                    }
                }
            }
        """
        executed = user_gql_client.execute(mutation, context=request)
        expected_data = {
            "renewMyYouthProfile": {"youthProfile": {"membershipStatus": "RENEWING"}}
        }
        assert dict(executed["data"]) == expected_data

    # Later in the year 2021, let's check our membership status
    with freeze_time("2021-09-01"):
        query = """
            {
                myYouthProfile {
                    membershipStatus
                }
            }
        """
        expected_data = {"myYouthProfile": {"membershipStatus": "EXPIRED"}}
        executed = user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data

    # Let's go back in time a few months and re-approve the membership
    with freeze_time("2021-05-02"):
        request.user = anon_user_gql_client.user

        t = Template(
            """
            mutation{
                approveYouthProfile(
                    input: {
                        approvalToken: "${token}",
                        approvalData: {}
                    }
                )
                {
                    youthProfile {
                        membershipStatus
                    }
                }
            }
            """
        )
        youth_profile.refresh_from_db()
        approval_data = {"token": youth_profile.approval_token}
        query = t.substitute(**approval_data)
        expected_data = {
            "approveYouthProfile": {"youthProfile": {"membershipStatus": "ACTIVE"}}
        }
        executed = anon_user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data


def test_youth_profile_expiration_should_be_renewable_by_staff_user(
    rf, user, staff_user_gql_client, anon_user_gql_client
):
    staff_user = staff_user_gql_client.user
    request = rf.post("/graphql")
    request.user = staff_user

    # Let's create a youth profile in the 2020
    with freeze_time("2020-05-02"):
        today = date.today()
        youth_profile = YouthProfileFactory(
            user=user,
            approved_time=datetime.today(),
            birth_date=today.replace(year=today.year - 15),
        )

    # In the year 2021, let's renew it
    with freeze_time("2021-05-01"):
        t = Template(
            """
            mutation {
                renewYouthProfile(input:{
                    id: \"${id}\"
                }) {
                    youthProfile {
                        membershipStatus
                    }
                }
            }
        """
        )
        mutation = t.substitute(
            id=to_global_id(type="YouthProfileNode", id=youth_profile.pk),
        )

        executed = staff_user_gql_client.execute(mutation, context=request)
        expected_data = {
            "renewYouthProfile": {"youthProfile": {"membershipStatus": "RENEWING"}}
        }
        assert dict(executed["data"]) == expected_data

    # Let's go back in time a few months and re-approve the membership
    with freeze_time("2021-05-02"):
        request.user = anon_user_gql_client.user

        t = Template(
            """
            mutation{
                approveYouthProfile(
                    input: {
                        approvalToken: "${token}",
                        approvalData: {}
                    }
                )
                {
                    youthProfile {
                        membershipStatus
                    }
                }
            }
            """
        )
        youth_profile.refresh_from_db()
        approval_data = {"token": youth_profile.approval_token}
        query = t.substitute(**approval_data)
        expected_data = {
            "approveYouthProfile": {"youthProfile": {"membershipStatus": "ACTIVE"}}
        }
        executed = anon_user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data


def test_youth_profile_expiration_for_over_18_years_old_should_renew_and_change_to_active(
    rf, user_gql_client, anon_user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    # Let's create a youth profile in the 2020
    with freeze_time("2020-05-02"):
        today = date.today()
        YouthProfileFactory(
            user=user_gql_client.user,
            approved_time=datetime.today(),
            birth_date=today.replace(year=today.year - 18, day=today.day - 1),
        )

    # In the year 2021, let's renew it
    with freeze_time("2021-05-01"):
        mutation = """
            mutation {
                renewMyYouthProfile(input:{}) {
                    youthProfile {
                        membershipStatus
                    }
                }
            }
        """
        executed = user_gql_client.execute(mutation, context=request)
        expected_data = {
            "renewMyYouthProfile": {"youthProfile": {"membershipStatus": "ACTIVE"}}
        }
        assert dict(executed["data"]) == expected_data


def test_should_not_be_able_to_renew_pending_youth_profile(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    with freeze_time("2020-05-15"):
        today = date.today()
        YouthProfileFactory(
            user=user_gql_client.user,
            birth_date=today.replace(year=today.year - 18, day=today.day - 1),
        )

    with freeze_time("2020-06-02"):

        # test query

        query = """
            {
                myYouthProfile {
                    membershipStatus
                    renewable
                }
            }
        """
        expected_data = {
            "myYouthProfile": {"membershipStatus": "PENDING", "renewable": False}
        }
        executed = user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data

        # test mutation

        mutation = """
            mutation {
                renewMyYouthProfile(input:{}) {
                    youthProfile {
                        membershipStatus
                    }
                }
            }
        """
        executed = user_gql_client.execute(mutation, context=request)
        assert (
            executed["errors"][0].get("extensions").get("code")
            == CANNOT_RENEW_YOUTH_PROFILE_ERROR
        )


def test_staff_user_can_create_youth_profile(
    rf, staff_user_gql_client, mocker, profile_api_response
):
    mocker.patch.object(ProfileAPI, "fetch_profile", return_value=profile_api_response)
    profile_id = from_global_id(profile_api_response["id"])[1]
    profile_global_id = to_global_id(type="YouthProfileNode", id=profile_id)

    user = staff_user_gql_client.user
    request = rf.post("/graphql")
    request.user = user
    today = date.today()
    birth_date = today.replace(year=today.year - 13) - timedelta(days=1)
    youth_profile_data = {
        "birth_date": birth_date.strftime("%Y-%m-%d"),
        "school_name": "Koulu",
        "school_class": "2B",
        "language_at_home": YouthLanguage.ENGLISH.name,
        "approver_first_name": "Jane",
        "approver_last_name": "Doe",
        "approver_phone": "040-1234567",
        "approver_email": "jane.doe@example.com",
    }

    t = Template(
        """
        mutation {
            createYouthProfile(
                input: {
                    id: \"${id}\",
                    youthProfile: {
                        birthDate: \"${birth_date}\",
                        schoolName: \"${school_name}\",
                        schoolClass: \"${school_class}\",
                        languageAtHome: ${language_at_home},
                        approverEmail: \"${approver_email}\",
                        approverPhone: \"${approver_phone}\",
                        approverFirstName: \"${approver_first_name}\",
                        approverLastName: \"${approver_last_name}\",
                    }
                    profileApiToken: "token"
                }
            ) {
                youthProfile {
                    id
                    birthDate
                    schoolName
                    schoolClass
                    languageAtHome
                    approverEmail
                    approverPhone
                    approverFirstName
                    approverLastName
                }
            }
        }
    """
    )
    query = t.substitute(
        id=profile_global_id,
        birth_date=youth_profile_data["birth_date"],
        school_name=youth_profile_data["school_name"],
        school_class=youth_profile_data["school_class"],
        language_at_home=youth_profile_data["language_at_home"],
        approver_email=youth_profile_data["approver_email"],
        approver_phone=youth_profile_data["approver_phone"],
        approver_first_name=youth_profile_data["approver_first_name"],
        approver_last_name=youth_profile_data["approver_last_name"],
    )
    expected_data = {
        "createYouthProfile": {
            "youthProfile": {
                "id": profile_global_id,
                "birthDate": youth_profile_data["birth_date"],
                "schoolName": youth_profile_data["school_name"],
                "schoolClass": youth_profile_data["school_class"],
                "languageAtHome": youth_profile_data["language_at_home"],
                "approverEmail": youth_profile_data["approver_email"],
                "approverPhone": youth_profile_data["approver_phone"],
                "approverFirstName": youth_profile_data["approver_first_name"],
                "approverLastName": youth_profile_data["approver_last_name"],
            }
        }
    }
    executed = staff_user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_staff_user_cannot_create_youth_profile_if_profile_does_not_exist(
    rf, staff_user_gql_client, mocker, profile_api_response
):
    mocker.patch.object(ProfileAPI, "fetch_profile", return_value={"id": ""})
    profile_id = from_global_id(profile_api_response["id"])[1]
    profile_global_id = to_global_id(type="YouthProfileNode", id=profile_id)

    user = staff_user_gql_client.user
    request = rf.post("/graphql")
    request.user = user
    today = date.today()
    birth_date = today.replace(year=today.year - 13) - timedelta(days=1)
    youth_profile_data = {
        "birth_date": birth_date.strftime("%Y-%m-%d"),
        "approver_email": "jane.doe@example.com",
    }

    t = Template(
        """
        mutation {
            createYouthProfile(
                input: {
                    id: \"${id}\",
                    youthProfile: {
                        birthDate: \"${birth_date}\",
                        approverEmail: \"${approver_email}\",
                    }
                    profileApiToken: "token"
                }
            ) {
                youthProfile {
                    id
                }
            }
        }
    """
    )
    query = t.substitute(
        id=profile_global_id,
        birth_date=youth_profile_data["birth_date"],
        approver_email=youth_profile_data["approver_email"],
    )
    executed = staff_user_gql_client.execute(query, context=request)
    assert (
        executed["errors"][0].get("extensions").get("code")
        == PROFILE_DOES_NOT_EXIST_ERROR
    )


def test_staff_user_can_create_youth_profile_for_under_13_years_old(
    rf, staff_user_gql_client, mocker, profile_api_response
):
    mocker.patch.object(ProfileAPI, "fetch_profile", return_value=profile_api_response)
    profile_id = from_global_id(profile_api_response["id"])[1]
    profile_global_id = to_global_id(type="YouthProfileNode", id=profile_id)

    user = staff_user_gql_client.user
    request = rf.post("/graphql")
    request.user = user

    today = date.today()
    birth_date = today.replace(year=today.year - 13) + timedelta(days=1)
    youth_profile_data = {
        "birth_date": birth_date.strftime("%Y-%m-%d"),
        "approver_email": "jane.doe@example.com",
    }

    t = Template(
        """
        mutation {
            createYouthProfile(
                input: {
                    id: \"${id}\",
                    youthProfile: {
                        birthDate: \"${birth_date}\",
                        approverEmail: \"${approver_email}\",
                    }
                    profileApiToken: "token"
                }
            ) {
                youthProfile {
                    id
                    birthDate
                    approverEmail
                }
            }
        }
    """
    )
    query = t.substitute(
        id=profile_global_id,
        birth_date=youth_profile_data["birth_date"],
        approver_email=youth_profile_data["approver_email"],
    )
    expected_data = {
        "createYouthProfile": {
            "youthProfile": {
                "id": profile_global_id,
                "birthDate": youth_profile_data["birth_date"],
                "approverEmail": youth_profile_data["approver_email"],
            }
        }
    }
    executed = staff_user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_normal_user_cannot_use_create_youth_profile_mutation(
    rf, user_gql_client, mocker, profile_api_response
):
    mocker.patch.object(ProfileAPI, "fetch_profile", return_value=profile_api_response)
    profile_id = from_global_id(profile_api_response["id"])[1]

    user = user_gql_client.user
    request = rf.post("/graphql")
    request.user = user

    today = date.today()
    birth_date = today.replace(year=today.year - 13) - timedelta(days=1)
    youth_profile_data = {
        "birth_date": birth_date.strftime("%Y-%m-%d"),
        "approver_email": "jane.doe@example.com",
    }

    t = Template(
        """
        mutation {
            createYouthProfile(
                input: {
                    id: \"${id}\",
                    youthProfile: {
                        birthDate: \"${birth_date}\",
                        approverEmail: \"${approver_email}\",
                    }
                    profileApiToken: "token"
                }
            ) {
                youthProfile {
                    id
                    birthDate
                    approverEmail
                }
            }
        }
    """
    )
    query = t.substitute(
        id=to_global_id(type="YouthProfileNode", id=profile_id),
        birth_date=youth_profile_data["birth_date"],
        approver_email=youth_profile_data["approver_email"],
    )
    executed = user_gql_client.execute(query, context=request)
    assert (
        executed["errors"][0].get("extensions").get("code") == PERMISSION_DENIED_ERROR
    )


def test_staff_user_can_cancel_youth_membership_on_selected_date(
    rf, staff_user_gql_client, youth_profile
):
    user = staff_user_gql_client.user
    request = rf.post("/graphql")
    request.user = user

    today = date.today()
    expiration_date = today + timedelta(days=1)
    youth_profile_data = {
        "id": to_global_id(type="YouthProfileNode", id=youth_profile.pk),
        "expiration": expiration_date.strftime("%Y-%m-%d"),
    }

    t = Template(
        """
        mutation {
            cancelYouthProfile(
                input: {
                    id: \"${id}\",
                    expiration: \"${expiration}\"
                }
            ) {
                youthProfile {
                    expiration
                }
            }
        }
    """
    )
    query = t.substitute(
        id=youth_profile_data["id"], expiration=youth_profile_data["expiration"],
    )
    expected_data = {
        "cancelYouthProfile": {
            "youthProfile": {"expiration": youth_profile_data["expiration"]}
        }
    }
    executed = staff_user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_staff_user_can_cancel_youth_membership_now(
    rf, staff_user_gql_client, youth_profile
):
    user = staff_user_gql_client.user
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        mutation {
            cancelYouthProfile(
                input: {
                    id: \"${id}\",
                }
            ) {
                youthProfile {
                    expiration
                }
            }
        }
    """
    )
    query = t.substitute(id=to_global_id(type="YouthProfileNode", id=youth_profile.pk))
    expected_data = {
        "cancelYouthProfile": {
            "youthProfile": {"expiration": date.today().strftime("%Y-%m-%d")}
        }
    }
    executed = staff_user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_normal_user_can_cancel_youth_membership(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    YouthProfileFactory(user=user_gql_client.user, approved_time=datetime.now())

    today = date.today()
    expiration = today + timedelta(days=1)
    expiration_string = expiration.strftime("%Y-%m-%d")

    t = Template(
        """
        mutation{
            cancelMyYouthProfile(
                input: {
                    expiration: \"${expiration}\"
                }
            )
            {
                youthProfile {
                    expiration
                    membershipStatus
                }
            }
        }
        """
    )
    query = t.substitute(expiration=expiration_string)

    expected_data = {
        "youthProfile": {"expiration": expiration_string, "membershipStatus": "EXPIRED"}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["cancelMyYouthProfile"]) == expected_data


def test_normal_user_can_cancel_youth_membership_now(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    YouthProfileFactory(user=user_gql_client.user, approved_time=datetime.now())

    query = """
        mutation{
            cancelMyYouthProfile(
                input: {}
            )
            {
                youthProfile {
                    expiration
                    membershipStatus
                }
            }
        }
    """
    expected_data = {
        "youthProfile": {
            "expiration": date.today().strftime("%Y-%m-%d"),
            "membershipStatus": "EXPIRED",
        }
    }

    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["cancelMyYouthProfile"]) == expected_data

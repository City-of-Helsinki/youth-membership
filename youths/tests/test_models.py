import datetime

import pytest
import pytz
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from freezegun import freeze_time

from youths.enums import MembershipStatus
from youths.models import YouthProfile
from youths.tests.factories import AdditionalContactPersonFactory
from youths.utils import generate_admin_group, user_is_admin


def test_serialize_youth_profile(youth_profile):
    AdditionalContactPersonFactory(youth_profile=youth_profile)
    serialized_youth_profile = youth_profile.serialize()

    expected = [
        {"key": "BIRTH_DATE", "value": youth_profile.birth_date.strftime("%Y-%m-%d")},
        {
            "key": "EXPIRATION",
            "value": youth_profile.expiration.strftime("%Y-%m-%d %H:%M"),
        },
        {"key": "APPROVER_FIRST_NAME", "value": youth_profile.approver_first_name},
        {"key": "APPROVER_LAST_NAME", "value": youth_profile.approver_last_name},
        {"key": "APPROVER_PHONE", "value": youth_profile.approver_phone},
        {"key": "APPROVER_EMAIL", "value": youth_profile.approver_email},
        {"key": "PHOTO_USAGE_APPROVED", "value": youth_profile.photo_usage_approved},
        {"key": "SCHOOL_NAME", "value": youth_profile.school_name},
        {"key": "SCHOOL_CLASS", "value": youth_profile.school_class},
        {"key": "LANGUAGE_AT_HOME", "value": youth_profile.language_at_home.value},
    ]

    expected_related = ["ADDITIONAL_CONTACT_PERSONS"]

    assert "key" in serialized_youth_profile
    assert "children" in serialized_youth_profile
    assert serialized_youth_profile["key"] == "YOUTHPROFILE"
    assert len(serialized_youth_profile["children"]) == len(expected) + len(
        expected_related
    )

    for d in expected:
        assert d in serialized_youth_profile["children"]

    # Check that related objects are included
    for key in expected_related:
        assert any(map(lambda x: x["key"] == key, serialized_youth_profile["children"]))


def test_serialize_additional_contact_person():
    acd = AdditionalContactPersonFactory()
    expected = [
        {"key": "FIRST_NAME", "value": acd.first_name},
        {"key": "LAST_NAME", "value": acd.last_name},
        {"key": "PHONE", "value": acd.phone},
        {"key": "EMAIL", "value": acd.email},
    ]

    serialized_acd = acd.serialize()

    assert "key" in serialized_acd
    assert "children" in serialized_acd
    assert serialized_acd["key"] == "ADDITIONALCONTACTPERSON"
    assert len(serialized_acd["children"]) == 4

    for d in expected:
        assert d in serialized_acd["children"]


def test_membership_number_is_generated_for_new_profile(settings, youth_profile):
    sequence_value = YouthProfile.membership_number_sequence.get_last_value()
    expected_number = str(sequence_value).zfill(settings.YOUTH_MEMBERSHIP_NUMBER_LENGTH)

    # Post save signal sets the membership number
    assert youth_profile.membership_number == expected_number

    # Post save signal saves the membership number into the DB
    youth_profile.refresh_from_db()
    assert youth_profile.membership_number == expected_number


def test_membership_number_is_generated_for_existing_profile(settings, youth_profile):
    """If membership number is empty, it will be generated."""
    original_number = YouthProfile.membership_number_sequence.get_last_value()

    youth_profile.membership_number = ""
    youth_profile.save()

    new_number = YouthProfile.membership_number_sequence.get_last_value()
    expected_number = str(new_number).zfill(settings.YOUTH_MEMBERSHIP_NUMBER_LENGTH)
    assert original_number < new_number
    assert youth_profile.membership_number == expected_number


def test_membership_number_is_not_changed_when_saving(youth_profile):
    expected_number = "MEMBER123"

    youth_profile.membership_number = expected_number
    youth_profile.save()

    assert youth_profile.membership_number == expected_number


def test_approving_profile_removes_access_tokens(youth_profile):
    youth_profile.profile_access_token = "token"
    youth_profile.profile_access_token_expiration = timezone.now()
    youth_profile.approval_token = "token"
    youth_profile.save()

    youth_profile.set_approved(save=True)

    youth_profile.refresh_from_db()
    assert youth_profile.profile_access_token == ""
    assert youth_profile.profile_access_token_expiration is None
    assert youth_profile.approval_token == ""


def test_additional_contact_person_runs_full_clean_when_saving(youth_profile):
    acp = AdditionalContactPersonFactory()
    with pytest.raises(ValidationError):
        acp.email = "notanemail"
        acp.save()


@pytest.mark.parametrize(
    "current_date,approved_time,expiration,status,renewable",
    [
        # Past the full season renewal date (approval)
        (
            "2020-05-10",
            datetime.datetime(2019, 8, 1),
            datetime.date(2020, 8, 31),
            MembershipStatus.ACTIVE,
            True,
        ),
        # Not yet past the full season renewal date
        (
            "2020-04-11",
            datetime.datetime(2019, 8, 1),
            datetime.date(2020, 8, 31),
            MembershipStatus.ACTIVE,
            False,
        ),
        # Waiting for approval by a guardian
        (
            "2020-05-12",
            None,
            datetime.date(2020, 8, 31),
            MembershipStatus.PENDING,
            False,
        ),
        # Past the expiration date
        (
            "2019-09-01",
            datetime.datetime(2019, 1, 1),
            datetime.date(2019, 8, 31),
            MembershipStatus.EXPIRED,
            True,
        ),
        # Expired pending registration
        (
            "2020-05-14",
            None,
            datetime.date(2019, 8, 31),
            MembershipStatus.EXPIRED,
            True,
        ),
        # Stale renewal i.e. has already expired
        (
            "2020-09-15",
            datetime.datetime(2019, 4, 30),
            datetime.date(2020, 8, 31),
            MembershipStatus.EXPIRED,
            True,
        ),
        # Approved after already expired
        (
            "2020-09-16",
            datetime.datetime(2020, 9, 16),
            datetime.date(2020, 8, 31),
            MembershipStatus.EXPIRED,
            True,
        ),
        # Full season renewal (next year)
        (
            "2020-05-17",
            datetime.datetime(2020, 1, 1),
            datetime.date(2021, 8, 31),
            MembershipStatus.RENEWING,
            False,
        ),
        # Full season renewal (next year), membership has expired, but renewal waiting for approval
        (
            "2020-09-01",
            datetime.datetime(2020, 1, 1),
            datetime.date(2021, 8, 31),
            MembershipStatus.PENDING,
            False,
        ),
        # Short season renewal, membership is expired, but it's waiting for approval
        (
            "2020-04-18",
            datetime.datetime(2019, 1, 1),
            datetime.date(2020, 8, 31),
            MembershipStatus.PENDING,
            False,
        ),
        # Last day of validity
        (
            "2020-08-31",
            datetime.datetime(2019, 8, 1),
            datetime.date(2020, 8, 31),
            MembershipStatus.ACTIVE,
            True,
        ),
        # Cancelled membership (calculated expiration, based on approved time, is after the expiration date)
        (
            "2020-05-15",
            datetime.datetime(2020, 1, 1),
            datetime.date(2020, 5, 14),
            MembershipStatus.EXPIRED,
            True,
        ),
        # Cancelled to a specific date, but still valid
        (
            "2020-05-15",
            datetime.datetime(2020, 1, 1),
            datetime.date(2020, 5, 16),
            MembershipStatus.ACTIVE,
            True,
        ),
    ],
)
def test_youth_profile_should_show_correct_membership_status(
    rf, youth_profile, current_date, approved_time, expiration, status, renewable
):
    youth_profile.approved_time = (
        approved_time.replace(tzinfo=pytz.UTC) if approved_time else approved_time
    )
    youth_profile.expiration = expiration
    youth_profile.save()

    with freeze_time(current_date):
        assert youth_profile.membership_status == status
        assert youth_profile.renewable == renewable


@pytest.mark.parametrize(
    "possible_admin_user,is_admin",
    [
        (pytest.lazy_fixture("anon_user"), False),
        (pytest.lazy_fixture("user"), False),
        (pytest.lazy_fixture("superuser"), True),
        (pytest.lazy_fixture("staff_user"), True),
    ],
)
def test_user_is_admin(possible_admin_user, is_admin):
    assert user_is_admin(possible_admin_user) == is_admin


def test_generate_admin_group():
    generate_admin_group()
    group = Group.objects.first()
    assert group.name == settings.YOUTH_MEMBERSHIP_STAFF_GROUP

import json
import logging

import pytest
from crum import impersonate

from youths.models import YouthProfile
from youths.tests.factories import YouthProfileFactory


@pytest.fixture(autouse=True)
def enable_audit_log(settings):
    settings.AUDIT_LOGGING_ENABLED = True
    settings.AUDIT_LOG_USERNAME = True


def get_log_records(caplog):
    """Return audit log messages.

    Format of record tuples is (logger_name, log_level, message).
    """
    return [
        log[2]
        for log in caplog.record_tuples
        if log[0] == "audit" and log[1] == logging.INFO
    ]


def assert_common_fields(log_message):
    assert log_message["audit_event"]["origin"] == "JASSARI-BE"
    assert log_message["audit_event"]["status"] == "SUCCESS"
    assert log_message["audit_event"]["actor"]["role"] == "SYSTEM"
    assert log_message["audit_event"]["date_time_epoch"] is not None
    assert log_message["audit_event"]["date_time"] is not None


def test_audit_log_read(user, caplog):
    YouthProfileFactory()
    caplog.clear()

    youth_profile = YouthProfile.objects.first()

    logs = get_log_records(caplog)
    assert len(logs) == 1
    log_message = json.loads(logs[0])
    assert_common_fields(log_message)
    assert log_message["audit_event"]["operation"] == "READ"
    assert log_message["audit_event"]["target"] == {
        "user_id": str(youth_profile.user.uuid),
        "user_name": youth_profile.user.username,
        "profile_id": str(youth_profile.pk),
        "profile_part": "YouthProfile",
    }


@pytest.mark.parametrize("role", ["SYSTEM", "OWNER", "ADMIN", "ANONYMOUS"])
def test_audit_log_read_actor_role(user, role, caplog, staff_user, anon_user):
    youth_profile = YouthProfileFactory()
    if role == "SYSTEM":
        user = None
    elif role == "OWNER":
        user = youth_profile.user
    elif role == "ADMIN":
        user = staff_user
    elif role == "ANONYMOUS":
        user = anon_user
    caplog.clear()

    with impersonate(user):
        YouthProfile.objects.first()

    logs = get_log_records(caplog)
    assert len(logs) == 1
    log_message = json.loads(logs[0])
    assert log_message["audit_event"]["actor"]["role"] == role
    if user:
        assert log_message["audit_event"]["actor"]["user_id"] == (
            str(user.uuid) if user != anon_user else None
        )
        assert log_message["audit_event"]["actor"]["user_name"] == user.username


def test_audit_log_update(user, youth_profile, caplog):
    caplog.clear()

    youth_profile.school_name = "Koulu X"
    youth_profile.save()

    logs = get_log_records(caplog)
    assert len(logs) == 1
    log_message = json.loads(logs[0])
    assert_common_fields(log_message)
    assert log_message["audit_event"]["operation"] == "UPDATE"
    assert log_message["audit_event"]["target"] == {
        "user_id": str(youth_profile.user.uuid),
        "user_name": youth_profile.user.username,
        "profile_id": str(youth_profile.pk),
        "profile_part": "YouthProfile",
    }


def test_audit_log_delete(user, enable_audit_log, youth_profile, caplog):
    caplog.clear()

    youth_profile.delete()

    logs = get_log_records(caplog)
    assert len(logs) == 1
    log_message = json.loads(logs[0])
    assert_common_fields(log_message)
    assert log_message["audit_event"]["operation"] == "DELETE"


def test_audit_log_create(user, caplog):
    caplog.clear()

    youth_profile = YouthProfileFactory()

    logs = get_log_records(caplog)
    assert len(logs) == 2  # profile is accessed here as well, thus the 2 log entries
    log_message = json.loads(logs[1])
    assert_common_fields(log_message)
    assert log_message["audit_event"]["operation"] == "CREATE"
    assert log_message["audit_event"]["target"] == {
        "user_id": str(youth_profile.user.uuid),
        "user_name": youth_profile.user.username,
        "profile_id": str(youth_profile.pk),
        "profile_part": "YouthProfile",
    }

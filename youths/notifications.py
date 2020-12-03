from django_ilmoitin.dummy_context import COMMON_CONTEXT, dummy_context
from django_ilmoitin.registry import notifications

from .enums import NotificationType

notifications.register(
    NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value,
    NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.label,
)
notifications.register(
    NotificationType.YOUTH_PROFILE_CONFIRMED.value,
    NotificationType.YOUTH_PROFILE_CONFIRMED.label,
)


dummy_context.update(
    {
        COMMON_CONTEXT: {
            "youth_name": "YOUTH NAME",
            "youth_profile": {"approver_first_name": "APPROVER FIRST NAME"},
        },
        NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value: {
            "youth_profile": {
                "approver_first_name": "APPROVER FIRST NAME",
                "approval_token": "approval_token",
                "profile_access_token": "profile_access_token",
            }
        },
    }
)

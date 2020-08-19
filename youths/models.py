import uuid
from datetime import date

import reversion
from django.conf import settings
from django.db import models
from django.utils import timezone
from django_ilmoitin.utils import send_notification
from enumfields import EnumField
from sequences import Sequence

from common_utils.models import SerializableMixin, UUIDModel

from .enums import NotificationType
from .enums import YouthLanguage as LanguageAtHome


def calculate_expiration(from_date=None):
    """Calculates the expiration date for a youth membership based on the given date.

    Membership always expires at the end of the season. Signups made before the long season start month
    expire in the summer of the same year, others next year.
    """
    if from_date is None:
        from_date = date.today()

    full_season_start = settings.YOUTH_MEMBERSHIP_FULL_SEASON_START_MONTH
    expiration_day, expiration_month = settings.YOUTH_MEMBERSHIP_SEASON_END_DATE
    expiration_year = (
        from_date.year + 1 if from_date.month >= full_season_start else from_date.year
    )
    return date(year=expiration_year, month=expiration_month, day=expiration_day)


@reversion.register()
class YouthProfile(UUIDModel, SerializableMixin):
    # TODO YouthProfile PK should be the same as is the Profile PK

    # Required info
    # TODO How to access Profile (backend) related information in new YouthProfile (backend)?
    # profile = models.OneToOneField(
    #     Profile, related_name="youth_profile", on_delete=models.CASCADE
    # )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE
    )
    # Post-save signal generates the membership number
    membership_number = models.CharField(max_length=16, blank=True)
    birth_date = models.DateField()
    school_name = models.CharField(max_length=128, blank=True)
    school_class = models.CharField(max_length=10, blank=True)
    expiration = models.DateField(default=calculate_expiration)

    language_at_home = EnumField(
        LanguageAtHome, max_length=32, default=LanguageAtHome.FINNISH
    )

    # Permissions
    approver_first_name = models.CharField(max_length=255, blank=True)
    approver_last_name = models.CharField(max_length=255, blank=True)
    approver_phone = models.CharField(max_length=50, blank=True)
    approver_email = models.EmailField(max_length=254, blank=True)
    approval_token = models.CharField(
        max_length=36, blank=True, default=uuid.uuid4, editable=False
    )
    approval_notification_timestamp = models.DateTimeField(
        null=True, blank=True, editable=False
    )
    approved_time = models.DateTimeField(null=True, blank=True, editable=False)
    photo_usage_approved = models.NullBooleanField()

    # Source sequence of integer values for a membership number.
    membership_number_sequence = Sequence("membership_number")

    def make_approvable(self):
        self.approval_token = uuid.uuid4()
        send_notification(
            email=self.approver_email,
            notification_type=NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value,
            context={"youth_profile": self},
            language=self.language_at_home.value,
        )
        self.approval_notification_timestamp = timezone.now()

    def __str__(self):
        if self.user:
            return "{} {} ({})".format(
                self.user.first_name, self.user.last_name, self.pk
            )
        else:
            return str(self.pk)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    serialize_fields = (
        {"name": "birth_date", "accessor": lambda x: x.strftime("%Y-%m-%d")},
        {"name": "school_name"},
        {"name": "school_class"},
        {"name": "language_at_home", "accessor": lambda x: x.value},
        {"name": "approver_first_name"},
        {"name": "approver_last_name"},
        {"name": "approver_phone"},
        {"name": "approver_email"},
        {"name": "expiration", "accessor": lambda x: x.strftime("%Y-%m-%d %H:%M")},
        {"name": "photo_usage_approved"},
        {"name": "additional_contact_persons"},
    )


class AdditionalContactPerson(SerializableMixin):
    youth_profile = models.ForeignKey(
        YouthProfile,
        on_delete=models.CASCADE,
        related_name="additional_contact_persons",
    )
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    email = models.EmailField(max_length=254)

    serialize_fields = (
        {"name": "first_name"},
        {"name": "last_name"},
        {"name": "phone"},
        {"name": "email"},
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.pk})"

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
import uuid
from datetime import date

import reversion
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_ilmoitin.utils import send_notification
from enumfields import EnumField
from sequences import Sequence

from common_utils.models import SerializableMixin, UUIDModel

from .enums import MembershipStatus, NotificationType
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
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE
    )
    # Post-save signal generates the membership number
    membership_number = models.CharField(
        max_length=16, blank=True, help_text=_("Youth's membership number")
    )
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

    profile_access_token = models.CharField(
        max_length=36,
        blank=True,
        help_text=_(
            "Temporary read access token for the profile linked to this youth profile."
        ),
    )
    profile_access_token_expiration = models.DateTimeField(null=True, blank=True)

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

    def set_approved(self, save=False):
        self.approved_time = timezone.now()
        self.approval_token = ""  # invalidate

        if save:
            self.save(update_fields=("approved_time", "approval_token"))

    @property
    def membership_status(self):
        if self.expiration <= date.today():
            return MembershipStatus.EXPIRED
        elif self.approved_time and self.approved_time <= timezone.now():
            # Status RENEWING implemented naively. Calculates the expiration for the existing approval time and checks
            # if expiration is set explicitly => status == EXPIRED. If expiration is greater than calculated expiration
            # for the current period, do one of the following:
            #
            # 1. If calculated expiration for approval time is in the past, membership is considered expired
            # 2. Otherwise status of the youth profile is RENEWING
            approved_period_expiration = calculate_expiration(self.approved_time.date())
            if self.expiration < approved_period_expiration:
                return MembershipStatus.EXPIRED
            elif self.expiration > approved_period_expiration:
                if date.today() <= approved_period_expiration:
                    return MembershipStatus.RENEWING
                else:
                    return MembershipStatus.EXPIRED
            return MembershipStatus.ACTIVE
        return MembershipStatus.PENDING

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

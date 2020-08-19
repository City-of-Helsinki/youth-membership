from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from reversion.admin import VersionAdmin

from youths.models import AdditionalContactPerson, YouthProfile


class AdditionalContactPersonInline(admin.StackedInline):
    model = AdditionalContactPerson
    extra = 0


@admin.register(YouthProfile)
class YouthProfileAdmin(VersionAdmin):
    inlines = (AdditionalContactPersonInline,)
    list_display = (
        "__str__",
        "membership_number",
    )
    readonly_fields = (
        "user",
        "membership_number",
        "approved_time",
        "approval_notification_timestamp",
    )
    search_fields = (
        "membership_number",
        "user__first_name",
        "user__last_name",
        "school_name",
        "school_class",
    )
    fieldsets = (
        (
            _("Youth profile basic information"),
            {
                "fields": (
                    "user",
                    "membership_number",
                    "birth_date",
                    "school_name",
                    "school_class",
                    "expiration",
                    "language_at_home",
                )
            },
        ),
        (
            _("Youth profile permissions"),
            {
                "fields": (
                    "approver_first_name",
                    "approver_last_name",
                    "approver_phone",
                    "approver_email",
                    "approval_notification_timestamp",
                    "approved_time",
                    "photo_usage_approved",
                )
            },
        ),
    )

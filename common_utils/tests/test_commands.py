import os

from django.core.management import call_command
from django.test import override_settings
from django_ilmoitin.models import NotificationTemplate

from common_utils.utils import EMAIL_GENERATED_PATH


def test_command_generate_notifications_from_templates_generates_notifications():
    assert NotificationTemplate.objects.count() == 0

    call_command("generate_notifications_from_templates")

    assert NotificationTemplate.objects.count() > 0


@override_settings(
    EMAIL_TEMPLATE_IMAGE_SOURCE="https://jassari.test.kuva.hel.ninja/email-templates",
    EMAIL_TEMPLATE_YOUTH_MEMBERSHIP_UI_BASE_URL="https://jassari.test.kuva.hel.ninja",
)
def test_command_generate_notifications_from_templates_generates_correct_looking_notifications(
    snapshot,
):
    call_command("generate_notifications_from_templates", "--dev")

    a_template_file = None

    with open(
        os.path.join(EMAIL_GENERATED_PATH, "youth_profile_confirmed_en.html"), "r"
    ) as generated_template:
        a_template_file = generated_template.read()

    snapshot.assert_match(a_template_file)

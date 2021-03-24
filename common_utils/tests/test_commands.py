import os

from django.core.management import call_command
from django_ilmoitin.models import NotificationTemplate

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EMAIL_TEMPLATES_PATH = os.path.join(PROJECT_ROOT, "templates", "email")
EMAIL_GENERATED_PATH = os.path.join(EMAIL_TEMPLATES_PATH, "generated")


def test_command_generate_notifications_from_templates_generates_notifications():
    assert NotificationTemplate.objects.count() == 0

    call_command("generate_notifications_from_templates")

    assert NotificationTemplate.objects.count() > 0


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

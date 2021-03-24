from django.core.management import call_command
from django_ilmoitin.models import NotificationTemplate


def test_command_generate_notifications_from_templates_generates_notifications():
    assert NotificationTemplate.objects.count() == 0

    call_command("generate_notifications_from_templates")

    assert NotificationTemplate.objects.count() > 0

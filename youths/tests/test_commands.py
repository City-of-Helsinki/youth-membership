from django.contrib.auth.models import Group
from django.core.management import call_command


def test_command_seed_data_creates_admin_group():
    call_command("seed_data")

    assert Group.objects.count() == 1

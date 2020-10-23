import pytest
from django.apps import apps
from django_ilmoitin.models import NotificationTemplate

from youths.utils import generate_notifications


@pytest.mark.parametrize("times", [1, 2])
def test_generate_notifications(times):
    """Test notifications are generated and that function can be run multiple times."""

    NotificationTemplateTranslation = apps.get_model(  # noqa: N806
        "django_ilmoitin", "NotificationTemplateTranslation"
    )

    for _i in range(times):
        generate_notifications()

    assert NotificationTemplate.objects.count() == 2
    assert NotificationTemplateTranslation.objects.count() == 6

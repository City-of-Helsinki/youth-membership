from datetime import date

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django_ilmoitin.models import NotificationTemplate
from graphql_relay import from_global_id

from common_utils.exceptions import InvalidEmailFormatError
from youths.enums import NotificationType
from youths.models import AdditionalContactPerson, YouthProfile


def generate_admin_group():
    group, created = Group.objects.get_or_create(
        name=settings.YOUTH_MEMBERSHIP_STAFF_GROUP
    )
    return group


def user_is_admin(user):
    return user.is_active and (
        user.is_superuser
        or user.is_staff
        or user.groups.filter(name=settings.YOUTH_MEMBERSHIP_STAFF_GROUP).exists()
    )


def calculate_age(birth_date):
    today = date.today()
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def create_or_update_contact_persons(youth_profile: YouthProfile, data):
    for data_input in filter(None, data):
        acp_global_id = data_input.pop("id", None)
        if acp_global_id:
            # id is required on update input
            acp_id = from_global_id(acp_global_id)[1]
            item = AdditionalContactPerson.objects.get(
                youth_profile=youth_profile, pk=acp_id
            )
        else:
            item = AdditionalContactPerson(youth_profile=youth_profile)

        for field, value in data_input.items():
            setattr(item, field, value)

        try:
            item.save()
        except ValidationError as e:
            if hasattr(e, "error_dict") and "email" in e.error_dict:
                raise InvalidEmailFormatError("Email must be in valid email format")
            else:
                raise


def delete_contact_persons(youth_profile: YouthProfile, data):
    for remove_global_id in filter(None, data):
        remove_id = from_global_id(remove_global_id)[1]
        AdditionalContactPerson.objects.get(
            youth_profile=youth_profile, pk=remove_id
        ).delete()


@transaction.atomic
def generate_notifications():
    """Creates Youth Profile notifications if they don't already exist."""

    if not NotificationTemplate.objects.filter(
        type=NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value
    ).exists():
        template = NotificationTemplate(
            type=NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value
        )
        fi_subject = "Vahvista nuorisojäsenyys"
        fi_html = (
            "Hei {{ youth_profile.approver_first_name }},<br /><br />{{ youth_name }} on "
            "pyytänyt sinua vahvistamaan nuorisojäsenyytensä. Käy antamassa vahvistus Jässäri-palvelussa käyttäen "
            'tätä linkkiä:<br /><br /><a href="https://jassari.test.kuva.hel.ninja/approve'
            '/{{ youth_profile.approval_token }}/{{ youth_profile.profile_access_token }}">'
            "https://jassari.test.kuva.hel.ninja/approve/{{ youth_profile.approval_token }}"
            "/{{ youth_profile.profile_access_token }}</a><br /><br /><i>Tämä viesti on lähetetty järjestelmästä "
            "automaattisesti. Älä vastaa tähän viestiin, sillä vastauksia ei käsitellä.</i>"
        )
        fi_text = (
            "Hei {{ youth_profile.approver_first_name }},\r\n\r\n{{ youth_name }} on pyytänyt "
            "sinua vahvistamaan nuorisojäsenyytensä. Käy antamassa vahvistus Jässäri-palvelussa käyttäen tätä linkkiä:"
            "\r\n\r\nhttps://jassari.test.kuva.hel.ninja/approve/{{ youth_profile.approval_token }}"
            "/{{ youth_profile.profile_access_token }}\r\n\r\nTämä viesti on lähetetty järjestelmästä automaattisesti. "
            "Älä vastaa tähän viestiin, sillä vastauksia ei käsitellä."
        )
        template.set_current_language("fi")
        template.subject = fi_subject
        template.body_html = fi_html
        template.body_text = fi_text
        template.set_current_language("sv")
        template.subject = fi_subject + " SV TRANSLATION NEEDED"
        template.body_html = fi_html + "<p>SV TRANSLATION NEEDED</p>"
        template.body_text = fi_text + "<p>SV TRANSLATION NEEDED</p>"
        template.set_current_language("en")
        template.subject = fi_subject + " EN TRANSLATION NEEDED"
        template.body_html = fi_html + "<p>EN TRANSLATION NEEDED</p>"
        template.body_text = fi_text + "<p>EN TRANSLATION NEEDED</p>"
        template.save()

    if not NotificationTemplate.objects.filter(
        type=NotificationType.YOUTH_PROFILE_CONFIRMED.value
    ).exists():
        template = NotificationTemplate(
            type=NotificationType.YOUTH_PROFILE_CONFIRMED.value
        )
        fi_subject = "Nuorisojäsenyys vahvistettu"
        fi_html = (
            "Hei {{ youth_name }},\r\n<br /><br />\r\n{{ youth_profile.approver_first_name }} on "
            "vahvistanut nuorisojäsenyytesi. Kirjaudu Jässäri-palveluun nähdäksesi omat tietosi:\r\n<br /><br />\r\n"
            '<a href="https://jassari.test.kuva.hel.ninja">https://jassari.test.kuva.hel.ninja</a>\r\n<br /><br />\r\n'
            "<i>Tämä viesti on lähetetty järjestelmästä automaattisesti. Älä vastaa tähän viestiin, sillä vastauksia "
            "ei käsitellä.</i>"
        )
        fi_text = (
            "Hei {{ youth_name }},\r\n\r\n{{ youth_profile.approver_first_name }} on vahvistanut "
            "nuorisojäsenyytesi. Kirjaudu Jässäri-palveluun nähdäksesi omat tietosi:\r\n\r\n"
            "https://jassari.test.kuva.hel.ninja\r\n\r\nTämä viesti on lähetetty järjestelmästä automaattisesti. Älä "
            "vastaa tähän viestiin, sillä vastauksia ei käsitellä."
        )
        template.set_current_language("fi")
        template.subject = fi_subject
        template.body_html = fi_html
        template.body_text = fi_text
        template.set_current_language("sv")
        template.subject = fi_subject + " SV TRANSLATION NEEDED"
        template.body_html = fi_html + "<p>SV TRANSLATION NEEDED</p>"
        template.body_text = fi_text + "<p>SV TRANSLATION NEEDED</p>"
        template.set_current_language("en")
        template.subject = fi_subject + " EN TRANSLATION NEEDED"
        template.body_html = fi_html + "<p>EN TRANSLATION NEEDED</p>"
        template.body_text = fi_text + "<p>EN TRANSLATION NEEDED</p>"
        template.save()

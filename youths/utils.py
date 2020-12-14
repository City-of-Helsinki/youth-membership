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


notification_templates = {
    NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value: {
        "fi": {
            "subject": (
                "{{ youth_name }} on lähettänyt hyväksyttäväksesi Helsingin kaupungin nuorisopalvelujen "
                "jäsenyyshakemuksen"
            ),
            "html": (
                "Hei {{ youth_profile.approver_first_name }},<br /><br />{{ youth_name }} on lähettänyt "
                "hyväksyttäväksesi Helsingin kaupungin nuorisopalvelujen jäsenyyshakemuksen. Jäsenyys on maksuton. "
                "Hyväksymällä hakemuksen, {{ youth_name }} voi käydä nuorisotalolla ja saa kivoja etuja. Mikäli "
                "tiedoissa on virheitä, pyydä nuorta muuttamaan tiedot ja lähettämään sinulle uusi varmistusviesti. "
                "Käy antamassa vahvistus Jässäri-palvelussa käyttäen tätä linkkiä:<br /><br />"
                '<a href="https://jassari.hel.fi/approve/{{ youth_profile.approval_token }}/'
                '{{ youth_profile.profile_access_token }}">https://jassari.hel.fi/approve/'
                "{{ youth_profile.approval_token }}/{{ youth_profile.profile_access_token }}</a><br /><br />"
                "<i>Tämä viesti on lähetetty järjestelmästä automaattisesti. Älä vastaa tähän viestiin, sillä "
                "vastauksia ei käsitellä.</i>"
            ),
            "text": (
                "Hei {{ youth_profile.approver_first_name }},\r\n\r\n{{ youth_name }} on lähettänyt hyväksyttäväksesi "
                "Helsingin kaupungin nuorisopalvelujen jäsenyyshakemuksen. Jäsenyys on maksuton. Hyväksymällä "
                "hakemuksen, {{ youth_name }} voi käydä nuorisotalolla ja saa kivoja etuja. Mikäli tiedoissa on "
                "virheitä, pyydä nuorta muuttamaan tiedot ja lähettämään sinulle uusi varmistusviesti. Käy antamassa "
                "vahvistus Jässäri-palvelussa käyttäen tätä linkkiä:\r\n\r\n"
                "https://jassari.hel.fi/approve/{{ youth_profile.approval_token }}/"
                "{{ youth_profile.profile_access_token }}\r\n\r\n"
                "Tämä viesti on lähetetty järjestelmistä automaattisesti. Älä vastaa tähän viestiin, sillä vastauksia "
                "ei käsitellä."
            ),
        },
        "sv": {
            "subject": (
                "{{ youth_name }} har skickat dig en ansökan om medlemskap i Helsingfors stads ungdomstjänster för "
                "godkännande."
            ),
            "html": (
                "Hej {{ youth_profile.approver_first_name }},<br /><br />{{ youth_name }} har skickat dig en ansökan "
                "om medlemskap i Helsingfors stads ungdomstjänster för godkännande. Medlemskapet är kostnadsfritt. Om "
                "du godkänner ansökan, kan {{ youth_name }} delta i ungdomsgårdarnas verksamhet och få trevliga "
                "förmåner. Om det finns fel i uppgifterna, be den unga att korrigera dem och sedan skicka ett nytt "
                "bekräftelsemeddelande till dig. Du kan ge ditt godkännande med Jässäri-tjänsten via denna länk:"
                '<br /><br /><a href="https://jassari.hel.fi/approve/{{ youth_profile.approval_token }}/'
                '{{ youth_profile.profile_access_token }}">https://jassari.hel.fi/approve/'
                "{{ youth_profile.approval_token }}/{{ youth_profile.profile_access_token }}</a><br /><br />"
                "<i>Det här meddelandet skickades automatiskt från våra system. Svara inte på det här meddelandet "
                "eftersom svaren inte kommer att behandlas.</i>"
            ),
            "text": (
                "Hej {{ youth_profile.approver_first_name }},\r\n\r\n{{ youth_name }} har skickat dig en ansökan "
                "om medlemskap i Helsingfors stads ungdomstjänster för godkännande. Medlemskapet är kostnadsfritt. "
                "Om du godkänner ansökan, kan {{ youth_name }} delta i ungdomsgårdarnas verksamhet och få trevliga "
                "förmåner. Om det finns fel i uppgifterna, be den unga att korrigera dem och sedan skicka ett nytt "
                "bekräftelsemeddelande till dig. Du kan ge ditt godkännande med Jässäri-tjänsten via denna länk:"
                "\r\n\r\nhttps://jassari.hel.fi/approve/{{ youth_profile.approval_token }}/"
                "{{ youth_profile.profile_access_token }}\r\n\r\nDet här meddelandet skickades automatiskt från våra "
                "system. Svara inte på det här meddelandet eftersom svaren inte kommer att behandlas."
            ),
        },
        "en": {
            "subject": (
                "{{ youth_name }} has sent a membership application for the City of Helsinki’s Youth Services for your "
                "approval."
            ),
            "html": (
                "Hi {{ youth_profile.approver_first_name }},<br /><br />{{ youth_name }} has sent a membership "
                "application for the City of Helsinki’s Youth Services for your approval. The membership is free of "
                "charge. If you approve the application, {{ youth_name }} may visit Youth Centres and enjoy fun "
                "benefits. If the information is incorrect, ask the youth to change it and send a new approval request "
                "to you. You can give your approval using the Jässäri service via this link:<br /><br />"
                '<a href="https://jassari.hel.fi/approve/{{ youth_profile.approval_token }}/'
                '{{ youth_profile.profile_access_token }}">https://jassari.hel.fi/approve/'
                "{{ youth_profile.approval_token }}/{{ youth_profile.profile_access_token }}</a><br /><br />"
                "<i>This message was sent automatically from our system. Please do not reply to this message as the "
                "replies will not be processed.</i>"
            ),
            "text": (
                "Hi {{ youth_profile.approver_first_name }},\r\n\r\n{{ youth_name }} has sent a membership application "
                "for the City of Helsinki’s Youth Services for your approval. The membership is free of charge. If you "
                "approve the application, {{ youth_name }} may visit Youth Centres and enjoy fun benefits. If the "
                "information is incorrect, ask the youth to change it and send a new approval request to you. You can "
                "give your approval using the Jässäri service via this link:\r\n\r\nhttps://jassari.hel.fi/approve/"
                "{{ youth_profile.approval_token }}/{{ youth_profile.profile_access_token }}\r\n\r\n"
                "This message was sent automatically from our system. Please do not reply to this message as the "
                "replies will not be processed."
            ),
        },
    },
    NotificationType.YOUTH_PROFILE_CONFIRMED.value: {
        "fi": {
            "subject": "{{ youth_profile.approver_first_name }} on hyväksynyt nuorisopalveluiden jäsenyytesi",
            "html": (
                "Tervetuloa Helsingin kaupungin nuorisopalveluiden jäseneksi! {{ youth_profile.approver_first_name }} "
                "on hyväksynyt jäsenyytesi. Digitaalinen jäsenkorttisi löytyy täältä: "
                '<a href="https://jassari.hel.fi">https://jassari.hel.fi</a><br /><br />'
                "Lisätietoa nuorisopalveluiden jäsenyydestä ja sen eduista voit lukea osoitteesta "
                '<a href="https://jassari.munstadi.fi/">https://jassari.munstadi.fi/</a>.<br /><br /><i>Tämä viesti on '
                "lähetetty järjestelmästä automaattisesti. Älä vastaa tähän viestiin, sillä vastauksia ei "
                "käsitellä.</i>"
            ),
            "text": (
                "Tervetuloa Helsingin kaupungin nuorisopalveluiden jäseneksi! {{ youth_profile.approver_first_name }} "
                "on hyväksynyt jäsenyytesi. Digitaalinen jäsenkorttisi löytyy täältä: https://jassari.hel.fi\r\n\r\n"
                "Lisätietoa nuorisopalveluiden jäsenyydestä ja sen eduista voit lukea osoitteesta "
                "https://jassari.munstadi.fi\r\n\r\nTämä viesti on lähetetty järjestelmästä automaattisesti. Älä "
                "vastaa tähän viestiin, sillä vastauksia ei käsitellä."
            ),
        },
        "sv": {
            "subject": (
                "{{ youth_profile.approver_first_name }} har godkänt ditt edlemskap i Helsingfors stads ungdomstjänster"
            ),
            "html": (
                "Välkommen som medlem i Helsingfors stads ungdomstjänster! {{ youth_profile.approver_first_name }} har "
                "godkänt ditt edlemskap i Helsingfors stads ungdomstjänster. Ditt digitala medlemskort kan hittas här: "
                '<a href="https://jassari.hel.fi">https://jassari.hel.fi</a><br /><br />'
                "Mer information om medlemskapet i ungdomstjänsterna och förmånerna finns på adressen "
                '<a href="https://jassari.munstadi.fi/sv/">https://jassari.munstadi.fi/sv/<a/><br /><br />'
                "<i>Det här meddelandet skickades automatiskt från våra system. Svara inte på det här meddelandet "
                "eftersom svaren inte kommer att behandlas.</i>"
            ),
            "text": (
                "Välkommen som medlem i Helsingfors stads ungdomstjänster! {{ youth_profile.approver_first_name }} har "
                "godkänt ditt edlemskap i Helsingfors stads ungdomstjänster. Ditt digitala medlemskort kan hittas här: "
                "https://jassari.hel.fi\r\n\r\nMer information om medlemskapet i ungdomstjänsterna och "
                "förmånerna finns på adressen https://jassari.munstadi.fi/sv/.\r\n\r\nDet här meddelandet skickades "
                "automatiskt från våra system. Svara inte på det här meddelandet eftersom svaren inte kommer att "
                "behandlas."
            ),
        },
        "en": {
            "subject": "{{ youth_profile.approver_first_name }} has approved your Youth Services membership",
            "html": (
                "Welcome to the Youth Services of the City of Helsinki! {{ youth_profile.approver_first_name }} has "
                "approved your membership. Your digital membership card can be found here: "
                '<a href="https://jassari.hel.fi">https://jassari.hel.fi</a><br /><br />For more information on the '
                "Youth Services membership and its perks, please visit "
                '<a href="https://jassari.munstadi.fi/en/">https://jassari.munstadi.fi/en/</a><br /><br />'
                "<i>This message was sent automatically from our system. Please do not reply to this message as the "
                "replies will not be processed.</i>"
            ),
            "text": (
                "Welcome to the Youth Services of the City of Helsinki! {{ youth_profile.approver_first_name }} has "
                "approved your membership. Your digital memberhsip card can be found here: "
                "https://jassari.hel.fi\r\n\r\nFor more information on the Youth Services membership and its perks, "
                "please visit https://jassari.munstadi.fi/en/.\r\n\r\nThis message was sent automatically from our "
                "system. Please do not reply to this message as the replies will not be processed."
            ),
        },
    },
}


@transaction.atomic
def generate_notifications():
    """Creates Youth Profile notifications if they don't already exist."""
    for notification_type, translations in notification_templates.items():

        if not NotificationTemplate.objects.filter(type=notification_type).exists():
            template = NotificationTemplate(type=notification_type)

            for lang, values in translations.items():
                template.set_current_language(lang)
                template.subject = values["subject"]
                template.body_html = values["html"]
                template.body_text = values["text"]
            template.save()

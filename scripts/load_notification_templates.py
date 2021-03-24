import os
import sys
from os import environ as env

from django.db import transaction
from paths import EMAIL_MESSAGES_PATH, EMAIL_PLAIN_MESSAGES_PATH
from script_logger import logger


def get_file_content(filepath):
    with open(filepath, "r") as f:
        return f.read()


@transaction.atomic
def load_email_templates(notifications, save=False):
    """Generates Youth Profile notifications from email templates and saves them into the database"""
    logger.info("Writing email templates")

    for notification_index, (notification_type, translations) in enumerate(
        notifications.items()
    ):

        template = NotificationTemplate.objects.create(
            id=notification_index,
            type=notification_type.value,
        )

        for lang, values in translations.items():

            with override(lang), switch_language(template, lang):
                template.subject = values.get("subject")

                if html_path := values.get("html"):
                    html_template_path = os.path.join(EMAIL_MESSAGES_PATH, html_path)
                    template_html_base = generate_template(html_template_path, save)

                    template.body_html = str(template_html_base)

                    logger.info(f"Generated template: {template} (html/{lang})")

                if plain_path := values.get("plain"):
                    plain_text_template_path = os.path.join(
                        EMAIL_PLAIN_MESSAGES_PATH, plain_path
                    )
                    template_text_base = get_file_content(plain_text_template_path)

                    template.body_text = str(template_text_base)

                    logger.info(f"Generated template: {template} (plain/{lang})")

                template.save()


if "DJANGO_SETTINGS_MODULE" not in env:
    from youth_membership import settings

    env.setdefault("DJANGO_SETTINGS_MODULE", settings.__name__)

if __name__ == "__main__":
    # Setup django
    import django

    django.setup()

    # The rest of the imports that depend on Django
    from django.utils.translation import override
    from django_ilmoitin.models import NotificationTemplate
    from parler.utils.context import switch_language

    from youths.enums import NotificationType as YouthNotificationType

    notifications = {
        YouthNotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED: {
            "fi": {
                "subject": (
                    "{{ youth_name }} on lähettänyt hyväksyttäväksesi Helsingin kaupungin nuorisopalvelujen "
                    "jäsenyyshakemuksen"
                ),
                "html": "youth_profile_confirmation_needed_fi.html",
                "plain": "youth_profile_confirmation_needed_fi.txt",
            },
            "sv": {
                "subject": (
                    "{{ youth_name }} har skickat dig en ansökan om medlemskap i Helsingfors stads ungdomstjänster för "
                    "godkännande."
                ),
                "html": "youth_profile_confirmation_needed_sv.html",
                "plain": "youth_profile_confirmation_needed_sv.txt",
            },
            "en": {
                "subject": (
                    "{{ youth_name }} has sent a membership application for the City of Helsinki’s Youth Services for "
                    "your approval."
                ),
                "html": "youth_profile_confirmation_needed_en.html",
                "plain": "youth_profile_confirmation_needed_en.txt",
            },
        },
        YouthNotificationType.YOUTH_PROFILE_CONFIRMED: {
            "fi": {
                "subject": "{{ youth_profile.approver_first_name }} on hyväksynyt nuorisopalveluiden jäsenyytesi",
                "html": "youth_profile_confirmed_fi.html",
                "plain": "youth_profile_confirmed_fi.txt",
            },
            "sv": {
                "subject": (
                    "{{ youth_profile.approver_first_name }} har godkänt ditt edlemskap i Helsingfors stads",
                    "ungdomstjänster",
                ),
                "html": "youth_profile_confirmed_sv.html",
                "plain": "youth_profile_confirmed_sv.txt",
            },
            "en": {
                "subject": "{{ youth_profile.approver_first_name }} has approved your Youth Services membership",
                "html": "youth_profile_confirmed_en.html",
                "plain": "youth_profile_confirmed_en.txt",
            },
        },
    }

    from scripts.generate_email_templates import generate_template

    logger.info("Cleaning existing notifications")
    delete_result = NotificationTemplate.objects.all().delete()
    logger.info(f"Deleted: {delete_result}")

    is_dev = "--dev" in sys.argv[1:]

    load_email_templates(notifications, is_dev)

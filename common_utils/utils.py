import json
import logging
import os
from pathlib import PurePath

from crum import get_current_request
from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.translation import override
from django_ilmoitin.models import NotificationTemplate
from parler.utils.context import switch_language

from youth_membership.settings import BASE_DIR
from youths.enums import NotificationType as YouthNotificationType

logger = logging.getLogger(__name__)

EMAIL_TEMPLATES_PATH = os.path.join(BASE_DIR, "templates")
EMAIL_GENERATED_PATH = os.path.join(EMAIL_TEMPLATES_PATH, "email", "generated")


def read_json_file(main: str, *args: str) -> dict:
    """Read and return the JSON content from a file.

    :param main: Path to which the JSON is relatively located (e.g. `__file__`)
    :param args: Parts of the path ending with the file (e.g. `"response", "r.json"`)
    :return: Dict containing file's JSON content.
    """
    path = PurePath(main).parent.joinpath(*args)
    with open(path.as_posix(), "r") as f:
        content = json.loads(f.read())
    return content


def get_original_client_ip():
    client_ip = None

    request = get_current_request()
    if request:
        if settings.USE_X_FORWARDED_FOR:
            forwarded_for = request.headers.get("x-forwarded-for", "")
            client_ip = forwarded_for.split(",")[0] or None

        if not client_ip:
            client_ip = request.META.get("REMOTE_ADDR")

    return client_ip


def create_generated_folder():
    if not os.path.exists(EMAIL_GENERATED_PATH):
        os.makedirs(EMAIL_GENERATED_PATH)


def save_template(filepath, content):
    create_generated_folder()

    if os.path.exists(filepath):
        os.remove(filepath)

    with open(filepath, "x") as f:
        f.write(content)


def get_file_content(filepath):
    with open(filepath, "r") as f:
        return f.read()


notifications = {
    YouthNotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED: {
        "fi": "{{ youth_name }} on lähettänyt hyväksyttäväksesi Helsingin kaupungin nuorisopalvelujen "
        "jäsenyyshakemuksen",
        "sv": "{{ youth_name }} har skickat dig en ansökan om medlemskap i Helsingfors stads ungdomstjänster för "
        "godkännande",
        "en": "{{ youth_name }} has sent a membership application for the City of Helsinki’s Youth Services for your "
        "approval",
        "fr": "{{ youth_name }} a envoyé une demande d'adhésion aux services pour la jeunesse de la ville de Helsinki "
        "pour la soumettre à votre acceptation",
        "ru": "{{ youth_name }} отправил/а вам для одобрения заявление о регистрации в сервисе для молодежи "
        "муниципалитета Хельсинки",
        "et": "{{ youth_name }} on saatnud kinnitamiseks Helsingi linna noorsoosteenuste liikmesuse taotluse",
        "so": "{{ youth_name }} ayaa kuu soo diray dalabka xubinimada adeegyada magaalada Helsinki si aad u "
        "ooggolaato",
        "ar": "{{ youth_name }} قد أرسل من أجل موافقتك طلب العضوية لخدمات الشباب لمدينة هلسنكي",
    },
    YouthNotificationType.YOUTH_PROFILE_CONFIRMED: {
        "fi": "{{ youth_profile.approver_first_name }} on hyväksynyt nuorisopalveluiden jäsenyytesi",
        "sv": "{{ youth_profile.approver_first_name }} har godkänt ditt edlemskap i Helsingfors stads ungdomstjänster",
        "en": "{{ youth_profile.approver_first_name }} has approved your Youth Services membership",
        "fr": "{{ youth_profile.approver_first_name }} a accepté votre adhésion aux services pour la jeunesse",
        "ru": "{{ youth_profile.approver_first_name }} одобрил/а ваше членство в сервисе для молодежи",
        "et": "{{ youth_profile.approver_first_name }} on kinnitanud noorsooteenuste liikmesuse",
        "so": "{{ youth_profile.approver_first_name }} ayaa la aqbalay xubinimadaadii adeegga dhallinyarada",
        "ar": "{{ youth_profile.approver_first_name }} قد وافق على عضويتك لدى خدمات الشباب",
    },
}


def get_notification_template_location(notification_type, lang):
    if notification_type == YouthNotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED:
        return {
            "html": f"email/messages/youth_profile_confirmation_needed_{lang}.html",
            "plain": f"email/plain_messages/youth_profile_confirmation_needed_{lang}.txt",
        }
    elif notification_type == YouthNotificationType.YOUTH_PROFILE_CONFIRMED:
        return {
            "html": f"email/messages/youth_profile_confirmed_{lang}.html",
            "plain": f"email/plain_messages/youth_profile_confirmed_{lang}.txt",
        }


@transaction.atomic
def generate_notifications(save=False):
    """Generates Youth Profile notifications from email templates and saves them into the database"""
    logger.info("Writing email templates")

    for notification_index, (notification_type, translations) in enumerate(
        notifications.items()
    ):

        template = NotificationTemplate.objects.create(
            id=notification_index,
            type=notification_type.value,
        )

        for lang, subject in translations.items():

            with override(lang), switch_language(template, lang):
                template.subject = subject
                template_location = get_notification_template_location(
                    notification_type, lang
                )

                # Html template generation
                template_html_base = render_to_string(
                    template_location["html"],
                    {"image_location": settings.EMAIL_TEMPLATE_IMAGE_SOURCE},
                )
                if save:
                    generated_template_filepath = os.path.join(
                        EMAIL_GENERATED_PATH,
                        os.path.basename(template_location["html"]),
                    )

                    save_template(generated_template_filepath, template_html_base)

                    logger.info(
                        f"Saved template into filesystem: {template} (html/{lang})"
                    )

                template.body_html = str(template_html_base)

                logger.info(f"Generated template: {template} (html/{lang})")

                # Plain template generation
                plain_text_template_path = os.path.join(
                    EMAIL_TEMPLATES_PATH, template_location["plain"]
                )
                template_text_base = get_file_content(plain_text_template_path)

                template.body_text = str(template_text_base)

                logger.info(f"Generated template: {template} (plain/{lang})")

                template.save()

import json

from django.core.management.base import BaseCommand
from django_ilmoitin.utils import send_notification

from youths.enums import NotificationType


def get_notification_data(notification_type):
    if notification_type == NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value:
        return {
            "notification_type": NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value,
            "context": {
                "youth_profile": {
                    "approver_first_name": "Sam",
                    "approval_token": "approval_token",
                    "profile_access_token": "profile_access_token",
                },
                "youth_name": "Test Youth",
                "youth_membership_ui_base_url": "https://jassari-ui/",
            },
        }
    elif notification_type == NotificationType.YOUTH_PROFILE_CONFIRMED.value:
        return {
            "notification_type": NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value,
            "context": {
                "youth_profile": {
                    "approver_first_name": "Sam",
                },
                "youth_name": "Test Youth",
                "youth_membership_ui_base_url": "https://jassari-ui/",
            },
        }


class Command(BaseCommand):
    help = "Created notification and sends it to the given email"

    def add_arguments(self, parser):
        parser.add_argument(
            "-e",
            "--email",
            help="The email the notification should be sent to",
        )
        parser.add_argument(
            "-nt",
            "--notification-type",
            help="The type of notification that should be sent",
        )
        parser.add_argument(
            "-c",
            "--context",
            help="Pass custom context to be used for the email",
            type=json.loads,
            default={},
        )

    def handle(self, *args, **options):
        email = options["email"]
        notification_type = options["notification_type"]
        custom_context = options["context"]

        if notification_data := get_notification_data(notification_type):
            notification_type = notification_data["notification_type"]
            default_context = notification_data["context"]

            notification = {
                "email": email,
                "language": "en",
                "context": {**default_context, **custom_context},
                "notification_type": notification_type,
            }

            try:
                send_notification(**notification)

                self.stdout.write(self.style.SUCCESS("Notification sent"))
                self.stdout.write(json.dumps(notification, indent=2))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error while sending notification: {e}")
                )
        else:
            self.stdout.write(
                self.style.ERROR("Did not send notification: Unknown notification type")
            )

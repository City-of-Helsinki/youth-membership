from django.core.management.base import BaseCommand
from django_ilmoitin.models import NotificationTemplate

from common_utils.utils import generate_notifications


class Command(BaseCommand):
    help = "Generates notifications from templates"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dev",
            action="store_true",
            help="Save generated templates into the filesystem for debugging",
        )

    def handle(self, *args, **options):
        self.stdout.write("Generating notifications")
        self.stdout.write("Cleaning existing notifications")
        delete_result = NotificationTemplate.objects.all().delete()
        self.stdout.write(f"Deleted: {delete_result}")

        is_dev = options["dev"]

        generate_notifications(is_dev)

        self.stdout.write(self.style.SUCCESS("Done - Generating notifications"))

from django.core.management.base import BaseCommand

from youths.utils import generate_admin_group, generate_notifications


class Command(BaseCommand):
    help = "Seed environment with initial data"

    def handle(self, *args, **kwargs):
        self.stdout.write("Creating/updating initial data")
        self.stdout.write("Generating admin the admin group...")
        generate_admin_group()
        self.stdout.write("Generating youth membership notifications...")
        generate_notifications()
        self.stdout.write(self.style.SUCCESS("Done - Initial data"))

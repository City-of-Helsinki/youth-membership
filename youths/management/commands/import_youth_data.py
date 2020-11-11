import json

from django.contrib.auth import get_user_model
from django.core import serializers
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.signals import post_save
from helusers.models import ADGroup, ADGroupMapping
from sequences.models import Sequence

from youths.models import YouthProfile
from youths.signals import generate_membership_number
from youths.utils import generate_admin_group

User = get_user_model()


class Command(BaseCommand):
    help = "Import youth data from a JSON file created using the open-city-profile backend's export_youth_data command."

    def add_arguments(self, parser):
        parser.add_argument("filename", nargs="+", type=str)

    def handle(self, *args, **kwargs):
        filename = kwargs["filename"][0]
        with open(filename, "r") as infile:
            data = json.load(infile)

        post_save.disconnect(generate_membership_number, sender=YouthProfile)

        with transaction.atomic():
            YouthProfile.objects.all().delete()
            User.objects.exclude(is_superuser=True).delete()
            ADGroup.objects.all().delete()

            User.objects.get_by_natural_key = lambda uuid: User.objects.get(uuid=uuid)
            ADGroup.objects.get_by_natural_key = lambda name: ADGroup.objects.get(
                name=name
            )
            YouthProfile.objects.get_by_natural_key = lambda uuid: YouthProfile.objects.get(
                id=uuid
            )

            max_membership_number = 0
            for obj in serializers.deserialize("json", json.dumps(data)):
                obj.save()

                if obj.object.__class__ == YouthProfile:
                    membership_number = int(obj.object.membership_number.lstrip("0"))
                    if membership_number > max_membership_number:
                        max_membership_number = membership_number

            Sequence.objects.filter(name="membership_number").update(
                last=max_membership_number
            )

            admin_group = generate_admin_group()
            for ad_group in ADGroup.objects.all():
                ADGroupMapping.objects.create(group=admin_group, ad_group=ad_group)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully read {get_user_model().objects.count()} users and "
                    f"{YouthProfile.objects.count()} from {filename}"
                )
            )

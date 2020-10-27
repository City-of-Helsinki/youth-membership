# Generated by Django 2.2.14 on 2020-10-27 07:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("youths", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="youthprofile",
            name="profile_access_token",
            field=models.CharField(
                blank=True,
                help_text="Temporary read access token for the profile linked to this youth profile.",
                max_length=36,
            ),
        ),
        migrations.AddField(
            model_name="youthprofile",
            name="profile_access_token_expiration",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

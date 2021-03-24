import os
import sys

from django.conf import settings
from jinja2 import Environment, FileSystemLoader
from paths import EMAIL_GENERATED_PATH, EMAIL_TEMPLATES_PATH
from script_logger import logger


def create_generated_folder():
    if not os.path.exists(EMAIL_GENERATED_PATH):
        os.makedirs(EMAIL_GENERATED_PATH)


def save_template(filepath, content):
    create_generated_folder()

    if os.path.exists(filepath):
        os.remove(filepath)

    with open(filepath, "x") as f:
        f.write(content)


def generate_template(template_source_path, save=False):
    with open(template_source_path, "r") as template_source_file:
        template_source = template_source_file.read()
        template = Environment(
            loader=FileSystemLoader(EMAIL_TEMPLATES_PATH)
        ).from_string(template_source)

        try:
            rendered = template.render(
                image_location=settings.EMAIL_TEMPLATE_IMAGE_SOURCE
            )

            if save:
                generated_template_filepath = os.path.join(
                    EMAIL_GENERATED_PATH, os.path.basename(template_source_file.name)
                )

                save_template(generated_template_filepath, rendered)

                logger.info(
                    f"Saved template {generated_template_filepath} into the filesystem"
                )

            return rendered

        except Exception:
            print("Unexpected error:", sys.exc_info()[0])
            raise

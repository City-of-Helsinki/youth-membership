from django.apps import AppConfig


class CommonUtilsConfig(AppConfig):
    name = "common_utils"

    def ready(self):
        import common_utils.audit_logging  # noqa isort:skip

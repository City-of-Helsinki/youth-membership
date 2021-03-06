import os
import subprocess
import sys

import environ
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

checkout_dir = environ.Path(__file__) - 2
assert os.path.exists(checkout_dir("manage.py"))

parent_dir = checkout_dir.path("..")
if os.path.isdir(parent_dir("etc")):
    env_file = parent_dir("etc/env")
    default_var_root = parent_dir("var")
else:
    env_file = checkout_dir(".env")
    default_var_root = checkout_dir("var")

env = environ.Env(
    DEBUG=(bool, True),
    TIER=(str, "dev"),  # one of: prod, qa, stage, test, dev
    SECRET_KEY=(str, ""),
    VAR_ROOT=(str, default_var_root),
    MEDIA_URL=(str, "/media/"),
    STATIC_URL=(str, "/static/"),
    ALLOWED_HOSTS=(list, []),
    DATABASE_URL=(
        str,
        "postgres://youth_membership:youth_membership@localhost/youth_membership",
    ),
    CACHE_URL=(str, "locmemcache://"),
    EMAIL_URL=(str, "consolemail://"),
    SENTRY_DSN=(str, ""),
    SENTRY_ENVIRONMENT=(str, "development"),
    TOKEN_AUTH_ACCEPTED_AUDIENCE=(str, ""),
    TOKEN_AUTH_ACCEPTED_SCOPE_PREFIX=(str, ""),
    TOKEN_AUTH_REQUIRE_SCOPE=(bool, False),
    TOKEN_AUTH_AUTHSERVER_URL=(str, ""),
    OIDC_CLIENT_ID=(str, ""),
    OIDC_CLIENT_SECRET=(str, ""),
    HELSINKI_PROFILE_API_URL=(str, ""),
    PROFILE_API_VERIFY=(bool, True),
    MAILER_EMAIL_BACKEND=(str, "django.core.mail.backends.console.EmailBackend"),
    DEFAULT_FROM_EMAIL=(str, "no-reply@hel.fi"),
    MAIL_MAILGUN_KEY=(str, ""),
    MAIL_MAILGUN_DOMAIN=(str, ""),
    MAIL_MAILGUN_API=(str, ""),
    NOTIFICATIONS_ENABLED=(bool, False),
    EMAIL_TEMPLATE_IMAGE_SOURCE=(str, ""),
    EMAIL_TEMPLATE_YOUTH_MEMBERSHIP_UI_BASE_URL=(str, ""),
    VERSION=(str, None),
    AUDIT_LOGGING_ENABLED=(bool, False),
    AUDIT_LOG_USERNAME=(bool, False),
    GDPR_API_QUERY_SCOPE=(str, ""),
    GDPR_API_DELETE_SCOPE=(str, ""),
    ENABLE_GRAPHIQL=(bool, False),
    FORCE_SCRIPT_NAME=(str, ""),
    CSRF_COOKIE_NAME=(str, ""),
    CSRF_COOKIE_PATH=(str, ""),
    CSRF_COOKIE_SECURE=(bool, None),
    SESSION_COOKIE_NAME=(str, ""),
    SESSION_COOKIE_PATH=(str, ""),
    SESSION_COOKIE_SECURE=(bool, None),
    USE_X_FORWARDED_HOST=(bool, None),
    USE_X_FORWARDED_FOR=(bool, False),
    CSRF_TRUSTED_ORIGINS=(list, []),
)
if os.path.exists(env_file):
    env.read_env(env_file)

version = env("VERSION")
if version is None:
    try:
        version = subprocess.check_output(["git", "describe", "--always"]).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        version = None

sentry_sdk.init(
    dsn=env("SENTRY_DSN"),
    release=version,
    environment=env("SENTRY_ENVIRONMENT"),
    integrations=[DjangoIntegration()],
)

sentry_sdk.integrations.logging.ignore_logger("graphql.execution.utils")

BASE_DIR = str(checkout_dir)
DEBUG = env("DEBUG")
TIER = env("TIER")
SECRET_KEY = env("SECRET_KEY")
if DEBUG and not SECRET_KEY:
    SECRET_KEY = "xxx"

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

if env("CSRF_COOKIE_NAME"):
    CSRF_COOKIE_NAME = env("CSRF_COOKIE_NAME")

if env("CSRF_COOKIE_PATH"):
    CSRF_COOKIE_PATH = env("CSRF_COOKIE_PATH")

if env("CSRF_COOKIE_SECURE") is not None:
    CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE")

if env("SESSION_COOKIE_NAME"):
    SESSION_COOKIE_NAME = env("SESSION_COOKIE_NAME")

if env("SESSION_COOKIE_PATH"):
    SESSION_COOKIE_PATH = env("SESSION_COOKIE_PATH")

if env("SESSION_COOKIE_SECURE") is not None:
    SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE")

USE_X_FORWARDED_FOR = env.bool("USE_X_FORWARDED_FOR")

if env("USE_X_FORWARDED_HOST") is not None:
    USE_X_FORWARDED_HOST = env("USE_X_FORWARDED_HOST")

if env("CSRF_TRUSTED_ORIGINS"):
    CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

DATABASES = {"default": env.db()}
# Ensure postgres engine
DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"

CACHES = {"default": env.cache()}
vars().update(env.email_url())  # EMAIL_BACKEND etc.

var_root = env.path("VAR_ROOT")
MEDIA_ROOT = var_root("media")
STATIC_ROOT = var_root("static")
MEDIA_URL = env("MEDIA_URL")
STATIC_URL = env("STATIC_URL")

ROOT_URLCONF = "youth_membership.urls"
WSGI_APPLICATION = "youth_membership.wsgi.application"

if env("FORCE_SCRIPT_NAME"):
    FORCE_SCRIPT_NAME = env("FORCE_SCRIPT_NAME")

LANGUAGES = (
    ("fi", "Finnish"),
    ("en", "English"),
    ("sv", "Swedish"),
    ("fr", "French"),
    ("ru", "Russian"),
    ("so", "Somali"),
    ("ar", "Arabic"),
    ("et", "Estonian"),
)

LANGUAGE_CODE = "fi"
TIME_ZONE = "Europe/Helsinki"
USE_I18N = True
USE_L10N = True
USE_TZ = True
# Set to True to enable GraphiQL interface, this will overridden to True if DEBUG=True
ENABLE_GRAPHIQL = env("ENABLE_GRAPHIQL")

INSTALLED_APPS = [
    # 3rd party
    "helusers.apps.HelusersConfig",
    "helusers.apps.HelusersAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "sequences.apps.SequencesConfig",
    "social_django",
    "django_filters",
    "parler",
    "corsheaders",
    "django_ilmoitin",
    "mailer",
    "graphene_django",
    "adminsortable",
    "import_export",
    # Local apps
    "users",
    "youths",
    "common_utils",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "crum.CurrentRequestUserMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    },
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "DIRS": [os.path.join(BASE_DIR, "templates/jinja2")],
    },
]

FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800

CORS_ORIGIN_ALLOW_ALL = True

# Authentication

AUTH_USER_MODEL = "users.User"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "admin:logout"

SESSION_SERIALIZER = "django.contrib.sessions.serializers.PickleSerializer"
SOCIAL_AUTH_TUNNISTAMO_AUTH_EXTRA_ARGUMENTS = {"ui_locales": "fi"}

SOCIAL_AUTH_TUNNISTAMO_KEY = env("OIDC_CLIENT_ID")
SOCIAL_AUTH_TUNNISTAMO_SECRET = env("OIDC_CLIENT_SECRET")
SOCIAL_AUTH_TUNNISTAMO_OIDC_ENDPOINT = env("TOKEN_AUTH_AUTHSERVER_URL")

HELSINKI_PROFILE_API_URL = env("HELSINKI_PROFILE_API_URL")
# Service type for this service in open-city-profile API
HELSINKI_PROFILE_SERVICE_TYPE = "YOUTH_MEMBERSHIP"

# Controls whether ProfileAPI verifies the server’s TLS certificate. Defaults to True.
PROFILE_API_VERIFY = env("PROFILE_API_VERIFY")

OIDC_API_TOKEN_AUTH = {
    "AUDIENCE": env("TOKEN_AUTH_ACCEPTED_AUDIENCE"),
    "API_SCOPE_PREFIX": env("TOKEN_AUTH_ACCEPTED_SCOPE_PREFIX"),
    "ISSUER": env("TOKEN_AUTH_AUTHSERVER_URL"),
    "REQUIRE_API_SCOPE_FOR_AUTHENTICATION": env("TOKEN_AUTH_REQUIRE_SCOPE"),
}

OIDC_AUTH = {"OIDC_LEEWAY": 60 * 60}

AUTHENTICATION_BACKENDS = [
    "helusers.tunnistamo_oidc.TunnistamoOIDCAuth",
    "django.contrib.auth.backends.ModelBackend",
    "common_utils.oidc.GraphQLApiTokenAuthentication",
]

# Django-parler

PARLER_LANGUAGES = {
    None: (
        {"code": "fi"},
        {"code": "en"},
        {"code": "sv"},
        {"code": "fr"},
        {"code": "ru"},
        {"code": "so"},
        {"code": "ar"},
        {"code": "et"},
    ),
    "default": {"fallbacks": ["fi"], "hide_untranslated": False},
}

PARLER_ENABLE_CACHING = False

# Notification settings

NOTIFICATIONS_ENABLED = True
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")
if env("MAIL_MAILGUN_KEY"):
    ANYMAIL = {
        "MAILGUN_API_KEY": env("MAIL_MAILGUN_KEY"),
        "MAILGUN_SENDER_DOMAIN": env("MAIL_MAILGUN_DOMAIN"),
        "MAILGUN_API_URL": env("MAIL_MAILGUN_API"),
    }
EMAIL_BACKEND = "mailer.backend.DbBackend"
MAILER_EMAIL_BACKEND = env("MAILER_EMAIL_BACKEND")
EMAIL_TEMPLATE_IMAGE_SOURCE = env("EMAIL_TEMPLATE_IMAGE_SOURCE")
EMAIL_TEMPLATE_YOUTH_MEMBERSHIP_UI_BASE_URL = env(
    "EMAIL_TEMPLATE_YOUTH_MEMBERSHIP_UI_BASE_URL"
)

# Graphene

GRAPHENE = {
    "SCHEMA": "youth_membership.schema.schema",
    "MIDDLEWARE": ["graphql_jwt.middleware.JSONWebTokenMiddleware"],
}

GRAPHQL_JWT = {"JWT_AUTH_HEADER_PREFIX": "Bearer"}

if "SECRET_KEY" not in locals():
    secret_file = os.path.join(BASE_DIR, ".django_secret")
    try:
        with open(secret_file) as f:
            SECRET_KEY = f.read().strip()
    except IOError:
        import random

        system_random = random.SystemRandom()
        try:
            SECRET_KEY = "".join(
                [
                    system_random.choice(
                        "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
                    )
                    for i in range(64)
                ]
            )
            with open(secret_file, "w") as f:
                import os

                os.fchmod(f.fileno(), 0o0600)
                f.write(SECRET_KEY)
                f.close()
        except IOError:
            Exception(
                "Please create a %s file with random characters to generate your secret key!"
                % secret_file
            )

# A youth membership number is the youth profile's PK padded with zeroes.
# This value tells what length the number will be padded to.
# For example, PK 123, length 6 --> 000123.
YOUTH_MEMBERSHIP_NUMBER_LENGTH = 6

# Date (day, month) for when the memberships are set to expire
YOUTH_MEMBERSHIP_SEASON_END_DATE = 31, 8

# Month from which on the membership will last until the next year, instead of ending in the current year
YOUTH_MEMBERSHIP_FULL_SEASON_START_MONTH = 5

YOUTH_MEMBERSHIP_STAFF_GROUP = "youth_admin"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "audit": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "ERROR"},
        "common_utils.audit_logging": {
            "handlers": ["audit"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": True,
        },
        "common_utils.utils": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}


GDPR_API_QUERY_SCOPE = env("GDPR_API_QUERY_SCOPE")
GDPR_API_DELETE_SCOPE = env("GDPR_API_DELETE_SCOPE")
GDPR_API_MODEL = "youths.YouthProfile"

AUDIT_LOGGING_ENABLED = env.bool("AUDIT_LOGGING_ENABLED")
AUDIT_LOG_USERNAME = env.bool("AUDIT_LOG_USERNAME")

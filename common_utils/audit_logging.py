import json
import logging

from crum import get_current_user
from django.conf import settings
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db import models
from django.db.models.signals import post_delete, post_init, post_save
from django.dispatch import receiver
from django.utils import timezone

from common_utils.signals import (
    token_authentication_failed,
    token_authentication_successful,
)
from common_utils.utils import get_original_client_ip

logger = logging.getLogger(__name__)


def _resolve_role(current_user, profile):
    """What is the role of the given user for the given profile."""
    if current_user:
        if profile.user == current_user:
            return "OWNER"
        elif current_user.is_authenticated:
            return "ADMIN"
        else:
            return "ANONYMOUS"
    else:
        return "SYSTEM"


def _format_user_data(audit_event, field_name, user):
    if user:
        if field_name not in audit_event:
            audit_event[field_name] = {}
        audit_event[field_name]["user_id"] = (
            str(user.uuid) if hasattr(user, "uuid") else None
        )
        if settings.AUDIT_LOG_USERNAME:
            audit_event[field_name]["user_name"] = (
                user.username if hasattr(user, "username") else None
            )


def _format_extra_info(audit_event, error=None):
    extra_info = {}

    ip_address = get_original_client_ip()
    if ip_address:
        extra_info["ip_address"] = ip_address
    if error:
        extra_info["error"] = error

    if extra_info:
        audit_event["extra_info"] = extra_info


def log(action, instance):
    if not (settings.AUDIT_LOGGING_ENABLED and instance.pk):
        return

    current_time = timezone.now()
    current_user = get_current_user()
    profile = instance.resolve_profile()
    profile_id = str(profile.pk) if profile else None
    target_user = profile.user if profile and profile.user else None

    message = {
        "audit_event": {
            "origin": "JASSARI-BE",
            "operation": action,
            "status": "SUCCESS",
            "date_time_epoch": int(current_time.timestamp()),
            "date_time": f"{current_time.replace(tzinfo=None).isoformat(sep='T', timespec='milliseconds')}Z",
            "actor": {"role": _resolve_role(current_user, profile)},
            "actor_service": {
                "id": "youth_membership",
                "name": "Youth Membership",
            },
            "target": {
                "profile_id": profile_id,
                "profile_part": instance.__class__.__name__,
            },
        }
    }

    _format_user_data(message["audit_event"], "actor", current_user)
    _format_user_data(message["audit_event"], "target", target_user)

    _format_extra_info(message["audit_event"])

    logger.info(json.dumps(message))


def log_auth(action, user=None, error=None):
    if not settings.AUDIT_LOGGING_ENABLED:
        return

    current_time = timezone.now()

    message = {
        "audit_event": {
            "origin": "JASSARI-BE",
            "operation": action,
            "status": "SUCCESS" if error is None else "FAILED",
            "date_time_epoch": int(current_time.timestamp()),
            "date_time": f"{current_time.replace(tzinfo=None).isoformat(sep='T', timespec='milliseconds')}Z",
            "actor_service": {
                "id": "youth_membership",
                "name": "Youth Membership",
            },
        }
    }

    _format_user_data(message["audit_event"], "actor", user)

    ip_address = get_original_client_ip()
    message["audit_event"]["jassaribe"] = {"ip_address": ip_address}

    _format_extra_info(message["audit_event"], error)

    logger.info(json.dumps(message))


def post_delete_audit_log(sender, instance, **kwargs):
    log("DELETE", instance)


def post_init_audit_log(sender, instance, **kwargs):
    log("READ", instance)


def post_save_audit_log(sender, instance, created, **kwargs):
    if created:
        log("CREATE", instance)
    else:
        log("UPDATE", instance)


class AuditLogModel(models.Model):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        post_init.connect(post_init_audit_log, cls)
        post_save.connect(post_save_audit_log, cls)
        post_delete.connect(post_delete_audit_log, cls)
        logger.debug(f"Audit logging signals connected for {cls}.")

    def resolve_profile(self):
        """Return the service main profile instance."""
        return self

    class Meta:
        abstract = True


@receiver(user_logged_in)
def user_logged_in_callback(sender, user, **kwargs):
    log_auth("LOGIN", user)


@receiver(user_logged_out)
def user_logged_out_callback(sender, user, **kwargs):
    log_auth("LOGOUT", user)


@receiver(user_login_failed)
def user_login_failed_callback(sender, credentials, **kwargs):
    log_auth("LOGIN", error=f"user login failed: {credentials}")


@receiver(token_authentication_successful)
def token_authentication_successful_callback(sender, user, **kwargs):
    log_auth("TOKEN_AUTH", user)


@receiver(token_authentication_failed)
def token_authentication_failed_callback(sender, error, **kwargs):
    log_auth("TOKEN_AUTH", error=error)

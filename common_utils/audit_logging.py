import json
import logging

from crum import get_current_user
from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete, post_init, post_save
from django.utils import timezone

logger = logging.getLogger("audit")


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
            "status": "SUCCESS",
            "date_time_epoch": int(current_time.timestamp()),
            "date_time": f"{current_time.isoformat(sep='T', timespec='milliseconds')}Z",
            "actor": {"role": _resolve_role(current_user, profile)},
            "actor_service": {
                "id": "youth_membership",
                "name": "Youth Membership",
            },
            "operation": action,
            "target": {
                "profile_id": profile_id,
                "profile_part": instance.__class__.__name__,
            },
        }
    }

    if current_user:
        message["audit_event"]["actor"]["user_id"] = (
            str(current_user.uuid) if hasattr(current_user, "uuid") else None
        )
        if settings.AUDIT_LOG_USERNAME:
            message["audit_event"]["actor"]["user_name"] = (
                current_user.username if hasattr(current_user, "username") else None
            )

    if target_user:
        message["audit_event"]["target"]["user_id"] = (
            str(target_user.uuid) if hasattr(target_user, "uuid") else None
        )
        if settings.AUDIT_LOG_USERNAME:
            message["audit_event"]["target"]["user_name"] = (
                target_user.username if hasattr(target_user, "username") else None
            )

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

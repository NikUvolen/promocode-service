from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from core.audit import log_audit_event
from core.models import AuditLog


@shared_task
def cleanup_expired_audit_logs_task():
    cutoff = timezone.now() - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
    deleted_count, _ = AuditLog.objects.filter(created_at__lt=cutoff).delete()
    log_audit_event(
        AuditLog.EventType.AUDIT_CLEANUP_COMPLETED,
        metadata={
            'deleted_count': deleted_count,
            'retention_days': settings.AUDIT_LOG_RETENTION_DAYS,
        },
    )
    return deleted_count

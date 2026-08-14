from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Q
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


def _fail_stale_jobs(model, event_type, now, queued_cutoff, running_cutoff):
    stale_condition = (
        Q(status=model.Status.QUEUED, created_at__lt=queued_cutoff)
        | Q(
            status=model.Status.RUNNING,
            started_at__lt=running_cutoff,
        )
        | Q(
            status=model.Status.RUNNING,
            started_at__isnull=True,
            created_at__lt=running_cutoff,
        )
    )
    update_fields = {
        'status': model.Status.FAILED,
        'finished_at': now,
        'error': (
            'Задача остановлена автоматически: превышено допустимое '
            'время ожидания или выполнения.'
        ),
    }
    updated_count = model.objects.filter(stale_condition).update(
        **update_fields,
    )
    if updated_count:
        log_audit_event(
            event_type,
            metadata={
                'reason': 'stale_background_job',
                'updated_count': updated_count,
            },
        )
    return updated_count


@shared_task
def fail_stale_background_jobs_task():
    from draws.models import DrawReport
    from promo.models import PromoCodeGeneration, PromoCodeImport

    now = timezone.now()
    queued_cutoff = now - timedelta(
        seconds=settings.BACKGROUND_JOB_QUEUE_TIMEOUT,
    )
    running_cutoff = now - timedelta(
        seconds=settings.BACKGROUND_JOB_RUNNING_TIMEOUT,
    )

    return {
        'promo_generations': _fail_stale_jobs(
            PromoCodeGeneration,
            AuditLog.EventType.PROMO_GENERATION_FAILED,
            now,
            queued_cutoff,
            running_cutoff,
        ),
        'promo_imports': _fail_stale_jobs(
            PromoCodeImport,
            AuditLog.EventType.PROMO_IMPORT_FAILED,
            now,
            queued_cutoff,
            running_cutoff,
        ),
        'draw_reports': _fail_stale_jobs(
            DrawReport,
            AuditLog.EventType.DRAW_REPORT_FAILED,
            now,
            queued_cutoff,
            running_cutoff,
        ),
    }

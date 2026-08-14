import smtplib
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from core.audit import log_audit_event
from core.models import AuditLog
from promo.models import PromoCodeGeneration, PromoCodeImport
from promo.services.generation import (
    generate_promo_codes,
    promo_code_generation_lock,
)
from promo.services.notifications import send_registration_email
from promo.services.xlsx_import import import_promo_codes


@shared_task(
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_registration_email_task(promo_code_id):
    send_registration_email(promo_code_id)


@shared_task(acks_late=True, reject_on_worker_lost=True)
def generate_promo_codes_task(generation_id):
    with promo_code_generation_lock():
        return _run_promo_code_generation(generation_id)


def _run_promo_code_generation(generation_id):
    generation = PromoCodeGeneration.objects.get(pk=generation_id)

    if generation.status == PromoCodeGeneration.Status.COMPLETED:
        return generation.generated_count

    generation.status = PromoCodeGeneration.Status.RUNNING
    generation.started_at = generation.started_at or timezone.now()
    generation.error = ''
    generation.save(update_fields=('status', 'started_at', 'error'))
    log_audit_event(
        AuditLog.EventType.PROMO_GENERATION_STARTED,
        actor=generation.created_by,
        target=generation,
        metadata={'requested_count': generation.requested_count},
    )

    try:
        generated_count = generate_promo_codes(generation.pk)
    except Exception as error:
        PromoCodeGeneration.objects.filter(pk=generation.pk).update(
            status=PromoCodeGeneration.Status.FAILED,
            error=str(error)[:2000],
            finished_at=timezone.now(),
        )
        log_audit_event(
            AuditLog.EventType.PROMO_GENERATION_FAILED,
            actor=generation.created_by,
            target=generation,
            metadata={
                'requested_count': generation.requested_count,
                'error': str(error)[:500],
            },
        )
        raise

    PromoCodeGeneration.objects.filter(pk=generation.pk).update(
        status=PromoCodeGeneration.Status.COMPLETED,
        generated_count=generated_count,
        finished_at=timezone.now(),
    )
    log_audit_event(
        AuditLog.EventType.PROMO_GENERATION_COMPLETED,
        actor=generation.created_by,
        target=generation,
        metadata={
            'requested_count': generation.requested_count,
            'generated_count': generated_count,
        },
    )
    return generated_count


@shared_task(acks_late=True, reject_on_worker_lost=True)
def import_promo_codes_task(import_id):
    import_job = PromoCodeImport.objects.get(pk=import_id)
    if import_job.status == PromoCodeImport.Status.COMPLETED:
        return import_job.imported_count

    import_job.status = PromoCodeImport.Status.RUNNING
    import_job.started_at = import_job.started_at or timezone.now()
    import_job.error = ''
    import_job.save(update_fields=('status', 'started_at', 'error'))
    log_audit_event(
        AuditLog.EventType.PROMO_IMPORT_STARTED,
        actor=import_job.created_by,
        target=import_job,
        metadata={'original_filename': import_job.original_filename},
    )

    try:
        result = import_promo_codes(import_id)
    except Exception as error:
        PromoCodeImport.objects.filter(pk=import_id).update(
            status=PromoCodeImport.Status.FAILED,
            error=str(error)[:2000],
            finished_at=timezone.now(),
        )
        log_audit_event(
            AuditLog.EventType.PROMO_IMPORT_FAILED,
            actor=import_job.created_by,
            target=import_job,
            metadata={
                'original_filename': import_job.original_filename,
                'error': str(error)[:500],
            },
        )
        raise

    PromoCodeImport.objects.filter(pk=import_id).update(
        status=PromoCodeImport.Status.COMPLETED,
        finished_at=timezone.now(),
    )
    log_audit_event(
        AuditLog.EventType.PROMO_IMPORT_COMPLETED,
        actor=import_job.created_by,
        target=import_job,
        metadata=result,
    )
    return result


@shared_task
def cleanup_expired_import_files_task():
    cutoff = timezone.now() - timedelta(
        days=settings.GENERATED_FILE_RETENTION_DAYS,
    )
    imports = PromoCodeImport.objects.filter(created_at__lt=cutoff).exclude(
        status=PromoCodeImport.Status.RUNNING,
    )
    deleted_count = 0

    for import_job in imports.iterator():
        changed_fields = []
        for field_name in ('source_file', 'error_file'):
            field = getattr(import_job, field_name)
            if not field:
                continue
            field.delete(save=False)
            setattr(import_job, field_name, '')
            changed_fields.append(field_name)
            deleted_count += 1
        if changed_fields:
            import_job.save(update_fields=changed_fields)

    return deleted_count

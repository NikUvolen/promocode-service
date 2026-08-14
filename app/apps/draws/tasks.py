import smtplib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings
from django.db import OperationalError
from django.utils import timezone

from core.audit import log_audit_event
from core.models import AuditLog
from draws.models import Draw, DrawReport
from draws.services.draw import run_draw
from draws.services.notifications import send_winner_email
from draws.services.reports import generate_draw_report


@shared_task(
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
    reject_on_worker_lost=True,
)
def send_winner_email_task(winner_id):
    return send_winner_email(winner_id)


@shared_task(
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_daily_draw_task():
    campaign_timezone = ZoneInfo(settings.TIME_ZONE)
    local_date = timezone.now().astimezone(campaign_timezone).date()
    draw_date = local_date - timedelta(days=1)
    already_completed = Draw.objects.filter(
        draw_date=draw_date,
        status=Draw.Status.COMPLETED,
    ).exists()
    try:
        draw = run_draw(
            draw_date=draw_date,
            trigger=Draw.Trigger.AUTOMATIC,
        )
    except Exception as error:
        log_audit_event(
            AuditLog.EventType.DRAW_FAILED,
            metadata={
                'draw_date': draw_date.isoformat(),
                'trigger': Draw.Trigger.AUTOMATIC,
                'error': str(error)[:500],
            },
        )
        raise
    log_audit_event(
        AuditLog.EventType.DRAW_COMPLETED,
        target=draw,
        metadata={
            'draw_date': draw.draw_date.isoformat(),
            'trigger': Draw.Trigger.AUTOMATIC,
            'winner_count': draw.winners.count(),
            'already_completed': already_completed,
        },
    )
    return {
        'draw_id': draw.pk,
        'draw_date': draw.draw_date.isoformat(),
        'winner_count': draw.winners.count(),
        'already_completed': already_completed,
    }


@shared_task(
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_manual_draw_task(draw_date, cutoff):
    draw_date = datetime.fromisoformat(draw_date).date()
    already_completed = Draw.objects.filter(
        draw_date=draw_date,
        status=Draw.Status.COMPLETED,
    ).exists()
    try:
        draw = run_draw(
            draw_date=draw_date,
            trigger=Draw.Trigger.MANUAL,
            cutoff=datetime.fromisoformat(cutoff),
        )
    except Exception as error:
        log_audit_event(
            AuditLog.EventType.DRAW_FAILED,
            metadata={
                'draw_date': draw_date.isoformat(),
                'trigger': Draw.Trigger.MANUAL,
                'cutoff': cutoff,
                'error': str(error)[:500],
            },
        )
        raise
    log_audit_event(
        AuditLog.EventType.DRAW_COMPLETED,
        target=draw,
        metadata={
            'draw_date': draw.draw_date.isoformat(),
            'trigger': Draw.Trigger.MANUAL,
            'winner_count': draw.winners.count(),
            'already_completed': already_completed,
        },
    )
    return {
        'draw_id': draw.pk,
        'draw_date': draw.draw_date.isoformat(),
        'winner_count': draw.winners.count(),
        'already_completed': already_completed,
    }


@shared_task(acks_late=True, reject_on_worker_lost=True)
def generate_draw_report_task(report_id):
    report = DrawReport.objects.get(pk=report_id)
    if report.status == DrawReport.Status.COMPLETED:
        return report.report_file.name

    report.status = DrawReport.Status.RUNNING
    report.started_at = report.started_at or timezone.now()
    report.error = ''
    report.save(update_fields=('status', 'started_at', 'error'))
    log_audit_event(
        AuditLog.EventType.DRAW_REPORT_STARTED,
        actor=report.created_by,
        target=report,
        metadata={},
    )

    try:
        filename = generate_draw_report(report_id)
    except Exception as error:
        DrawReport.objects.filter(pk=report_id).update(
            status=DrawReport.Status.FAILED,
            error=str(error)[:2000],
            finished_at=timezone.now(),
        )
        log_audit_event(
            AuditLog.EventType.DRAW_REPORT_FAILED,
            actor=report.created_by,
            target=report,
            metadata={'error': str(error)[:500]},
        )
        raise

    DrawReport.objects.filter(pk=report_id).update(
        status=DrawReport.Status.COMPLETED,
        finished_at=timezone.now(),
    )
    log_audit_event(
        AuditLog.EventType.DRAW_REPORT_COMPLETED,
        actor=report.created_by,
        target=report,
        metadata={'filename': filename},
    )
    return filename


@shared_task
def cleanup_expired_report_files_task():
    cutoff = timezone.now() - timedelta(
        days=settings.GENERATED_FILE_RETENTION_DAYS,
    )
    reports = DrawReport.objects.filter(created_at__lt=cutoff).exclude(
        status=DrawReport.Status.RUNNING,
    )
    deleted_count = 0

    for report in reports.iterator():
        if not report.report_file:
            continue
        report.report_file.delete(save=False)
        report.report_file = ''
        report.save(update_fields=('report_file',))
        deleted_count += 1

    return deleted_count

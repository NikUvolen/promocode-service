import smtplib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings
from django.db import OperationalError
from django.utils import timezone

from draws.models import Draw
from draws.services.draw import run_draw
from draws.services.notifications import send_winner_email


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
    draw = run_draw(
        draw_date=draw_date,
        trigger=Draw.Trigger.AUTOMATIC,
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
    draw = run_draw(
        draw_date=draw_date,
        trigger=Draw.Trigger.MANUAL,
        cutoff=datetime.fromisoformat(cutoff),
    )
    return {
        'draw_id': draw.pk,
        'draw_date': draw.draw_date.isoformat(),
        'winner_count': draw.winners.count(),
        'already_completed': already_completed,
    }

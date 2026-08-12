from datetime import timedelta
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings
from django.db import OperationalError
from django.utils import timezone

from draws.models import Draw
from draws.services.draw import run_draw


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
    draw = run_draw(
        draw_date=local_date - timedelta(days=1),
        trigger=Draw.Trigger.AUTOMATIC,
    )
    return {
        'draw_id': draw.pk,
        'draw_date': draw.draw_date.isoformat(),
        'winner_count': draw.winners.count(),
    }

import secrets
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from draws.models import Draw, Winner
from draws.services.locks import lock_draw_date
from promo.models import PromoCode


DAILY_PRIZES = (Winner.Prize.OZON_3000, Winner.Prize.AIRPODS)


class InvalidDrawPeriod(ValueError):
    pass


def get_draw_period(draw_date, cutoff=None):
    campaign_timezone = ZoneInfo(settings.TIME_ZONE)
    starts_at = datetime.combine(draw_date, time.min, campaign_timezone)
    ends_at = starts_at + timedelta(days=1)
    cutoff = cutoff or ends_at

    if timezone.is_naive(cutoff):
        raise InvalidDrawPeriod('Draw cutoff must be timezone-aware.')

    cutoff = min(cutoff, ends_at)
    if cutoff <= starts_at:
        raise InvalidDrawPeriod('Draw cutoff must be after the period start.')

    return starts_at, cutoff


def run_draw(*, draw_date, trigger, cutoff=None):
    starts_at, ends_at = get_draw_period(draw_date, cutoff)

    with transaction.atomic():
        lock_draw_date(draw_date)
        draw, _ = Draw.objects.get_or_create(
            draw_date=draw_date,
            defaults={'trigger': trigger},
        )

        if draw.status == Draw.Status.COMPLETED:
            return draw

        started_at = timezone.now()
        draw.status = Draw.Status.RUNNING
        draw.trigger = trigger
        draw.started_at = draw.started_at or started_at
        draw.completed_at = None
        draw.save(
            update_fields=(
                'status',
                'trigger',
                'started_at',
                'completed_at',
                'updated_at',
            )
        )

        existing_prizes = set(
            draw.winners.values_list('prize', flat=True)
        )
        for prize in DAILY_PRIZES:
            if prize in existing_prizes:
                continue
            promo_code = _select_winning_code(
                starts_at=starts_at,
                ends_at=ends_at,
            )
            if promo_code is None:
                break
            Winner.objects.create(
                draw=draw,
                user_id=promo_code.registered_by_id,
                promo_code=promo_code,
                prize=prize,
            )

        draw.status = Draw.Status.COMPLETED
        draw.completed_at = timezone.now()
        draw.save(
            update_fields=('status', 'completed_at', 'updated_at')
        )
        return draw


def _select_winning_code(*, starts_at, ends_at):
    candidates = (
        PromoCode.objects.filter(
            registered_at__gte=starts_at,
            registered_at__lt=ends_at,
            registered_by__isnull=False,
        )
        .exclude(registered_by__wins__isnull=False)
        .order_by('pk')
    )
    count = candidates.count()
    if count == 0:
        return None
    return candidates[secrets.randbelow(count)]

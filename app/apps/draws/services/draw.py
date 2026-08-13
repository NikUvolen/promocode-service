import secrets
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from draws.models import Draw, Winner
from draws.services.locks import lock_draw_operation
from draws.services.notifications import schedule_winner_emails
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


def get_period_start(*, draw_date, ends_at):
    previous_end = (
        Draw.objects.filter(
            status=Draw.Status.COMPLETED,
            period_ended_at__isnull=False,
            period_ended_at__lt=ends_at,
        )
        .order_by('-period_ended_at')
        .values_list('period_ended_at', flat=True)
        .first()
    )
    if previous_end is not None:
        return previous_end
    return get_draw_period(draw_date)[0]


def run_draw(*, draw_date, trigger, cutoff=None):
    if trigger == Draw.Trigger.MANUAL and cutoff is None:
        cutoff = timezone.now()
    _, ends_at = get_draw_period(draw_date, cutoff)

    with transaction.atomic():
        lock_draw_operation()
        draw, _ = Draw.objects.get_or_create(
            draw_date=draw_date,
            defaults={'trigger': trigger},
        )

        if draw.status == Draw.Status.COMPLETED:
            _schedule_unnotified_winners(draw)
            return draw

        starts_at = get_period_start(
            draw_date=draw_date,
            ends_at=ends_at,
        )
        if starts_at >= ends_at:
            raise InvalidDrawPeriod(
                'Draw period must start before its cutoff.'
            )

        started_at = timezone.now()
        draw.status = Draw.Status.RUNNING
        draw.trigger = trigger
        draw.started_at = draw.started_at or started_at
        draw.completed_at = None
        draw.period_started_at = starts_at
        draw.period_ended_at = ends_at
        draw.save(
            update_fields=(
                'status',
                'trigger',
                'started_at',
                'completed_at',
                'period_started_at',
                'period_ended_at',
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
        _schedule_unnotified_winners(draw)
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


def _schedule_unnotified_winners(draw):
    winner_ids = list(
        draw.winners.filter(notified_at__isnull=True).values_list(
            'pk', flat=True
        )
    )
    if winner_ids:
        transaction.on_commit(
            lambda: schedule_winner_emails(winner_ids)
        )

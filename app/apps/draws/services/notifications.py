import logging
import smtplib

from django.conf import settings
from django.core.mail import send_mail
from django.core.cache import cache
from django.utils import timezone

from draws.models import Winner


logger = logging.getLogger(__name__)


def send_winner_email(winner_id):
    lock_key = f'winner-email-lock:{winner_id}'
    if not cache.add(lock_key, True, timeout=5 * 60):
        return False

    try:
        try:
            winner = Winner.objects.select_related(
                'user', 'promo_code', 'draw'
            ).get(pk=winner_id)
        except Winner.DoesNotExist:
            return False

        if winner.notified_at is not None:
            return False

        sent_count = send_mail(
            subject='Вы выиграли приз',
            message=(
                'Поздравляем! Ваш промокод '
                f'{winner.promo_code.code} выиграл приз '
                f'«{winner.get_prize_display()}» в розыгрыше '
                f'за {winner.draw.draw_date:%d.%m.%Y}.\n\n'
                'Мы свяжемся с вами для передачи приза.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[winner.user.email],
        )
        if sent_count != 1:
            raise smtplib.SMTPException('Winner email was not accepted.')
        Winner.objects.filter(pk=winner_id, notified_at__isnull=True).update(
            notified_at=timezone.now()
        )
        return True
    finally:
        cache.delete(lock_key)


def schedule_winner_emails(winner_ids):
    from draws.tasks import send_winner_email_task

    for winner_id in winner_ids:
        try:
            send_winner_email_task.delay(winner_id)
        except Exception:
            logger.exception(
                'Failed to enqueue winner email for winner %s',
                winner_id,
            )

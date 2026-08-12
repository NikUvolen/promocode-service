import logging

from django.conf import settings
from django.core.mail import send_mail

from promo.models import PromoCode


logger = logging.getLogger(__name__)


def send_registration_email(promo_code_id):
    try:
        promo_code = PromoCode.objects.select_related(
            'registered_by__profile'
        ).get(pk=promo_code_id, registered_by__isnull=False)
    except PromoCode.DoesNotExist:
        return

    user = promo_code.registered_by
    if not user.profile.promo_code_email_notifications:
        return

    send_mail(
        subject='Промокод зарегистрирован',
        message=(
            f'Промокод {promo_code.code} успешно зарегистрирован.\n\n'
            'Он участвует в ближайшем ежедневном розыгрыше.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def schedule_registration_email(promo_code_id):
    from promo.tasks import send_registration_email_task

    try:
        send_registration_email_task.delay(promo_code_id)
    except Exception:
        logger.exception(
            'Failed to enqueue promo code email for code %s',
            promo_code_id,
        )

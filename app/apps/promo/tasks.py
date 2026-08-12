import smtplib

from celery import shared_task
from django.utils import timezone

from promo.models import PromoCodeGeneration
from promo.services.generation import (
    generate_promo_codes,
    promo_code_generation_lock,
)
from promo.services.notifications import send_registration_email


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

    try:
        generated_count = generate_promo_codes(generation.pk)
    except Exception as error:
        PromoCodeGeneration.objects.filter(pk=generation.pk).update(
            status=PromoCodeGeneration.Status.FAILED,
            error=str(error)[:2000],
            finished_at=timezone.now(),
        )
        raise

    PromoCodeGeneration.objects.filter(pk=generation.pk).update(
        status=PromoCodeGeneration.Status.COMPLETED,
        generated_count=generated_count,
        finished_at=timezone.now(),
    )
    return generated_count

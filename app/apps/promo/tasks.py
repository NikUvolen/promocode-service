import smtplib

from celery import shared_task

from promo.services.notifications import send_registration_email


@shared_task(
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_registration_email_task(promo_code_id):
    send_registration_email(promo_code_id)

import smtplib

from celery import shared_task

from accounts.services.email_verification import send_verification_email
from accounts.services.passwords import send_password_reset_email


@shared_task(
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_verification_email_task(user_id):
    send_verification_email(user_id)


@shared_task(
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_password_reset_email_task(user_id):
    send_password_reset_email(user_id)

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction

from accounts.models import User


logger = logging.getLogger(__name__)
EMAIL_VERIFICATION_SALT = 'accounts.email-verification'


class InvalidEmailVerificationToken(Exception):
    pass


def create_email_verification_token(user):
    return signing.dumps(
        {'user_id': user.pk, 'email': user.email},
        salt=EMAIL_VERIFICATION_SALT,
        compress=True,
    )


def send_verification_email(user_id):
    try:
        user = User.objects.get(pk=user_id, is_email_verified=False)
    except User.DoesNotExist:
        return

    token = create_email_verification_token(user)
    query = urlencode({'token': token})
    verification_url = (
        f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?{query}"
    )
    send_mail(
        subject='Подтверждение email',
        message=(
            'Подтвердите адрес электронной почты, перейдя по ссылке:\n\n'
            f'{verification_url}\n\n'
            'Если вы не регистрировались, проигнорируйте это письмо.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def schedule_verification_email(user_id):
    from accounts.tasks import send_verification_email_task

    try:
        send_verification_email_task.delay(user_id)
    except Exception:
        logger.exception(
            'Failed to enqueue verification email for user %s',
            user_id,
        )


def verify_email(token):
    try:
        payload = signing.loads(
            token,
            salt=EMAIL_VERIFICATION_SALT,
            max_age=settings.EMAIL_VERIFICATION_TIMEOUT,
        )
    except (signing.BadSignature, signing.SignatureExpired) as exc:
        raise InvalidEmailVerificationToken from exc

    try:
        with transaction.atomic():
            user = User.objects.select_for_update().get(
                pk=payload['user_id'],
                email=payload['email'],
            )
            if not user.is_email_verified:
                user.is_email_verified = True
                user.save(update_fields=('is_email_verified',))
    except (KeyError, User.DoesNotExist) as exc:
        raise InvalidEmailVerificationToken from exc

    return user

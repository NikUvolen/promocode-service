import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from accounts.models import User
from accounts.services.authentication import blacklist_user_refresh_tokens


logger = logging.getLogger(__name__)


class InvalidPasswordResetToken(Exception):
    pass


class InvalidNewPassword(Exception):
    def __init__(self, messages):
        self.messages = messages
        super().__init__(*messages)


class InvalidOldPassword(Exception):
    pass


def create_password_reset_credentials(user):
    return {
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
    }


def send_password_reset_email(user_id):
    try:
        user = User.objects.get(
            pk=user_id,
            is_active=True,
            is_email_verified=True,
        )
    except User.DoesNotExist:
        return

    query = urlencode(create_password_reset_credentials(user))
    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?{query}"
    send_mail(
        subject='Восстановление пароля',
        message=(
            'Для восстановления пароля перейдите по ссылке:\n\n'
            f'{reset_url}\n\n'
            'Если вы не запрашивали восстановление, проигнорируйте письмо.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def schedule_password_reset_email(user_id):
    from accounts.tasks import send_password_reset_email_task

    try:
        send_password_reset_email_task.delay(user_id)
    except Exception:
        logger.exception(
            'Failed to enqueue password reset email for user %s',
            user_id,
        )


def request_password_reset(email):
    normalized_email = User.objects.normalize_email(email).lower()
    user = User.objects.filter(
        email=normalized_email,
        is_active=True,
        is_email_verified=True,
    ).first()
    if user is not None and user.has_usable_password():
        schedule_password_reset_email(user.pk)


def reset_password(*, uid, token, new_password):
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id, is_active=True)
    except (TypeError, ValueError, OverflowError, UnicodeDecodeError, User.DoesNotExist) as exc:
        raise InvalidPasswordResetToken from exc

    if not default_token_generator.check_token(user, token):
        raise InvalidPasswordResetToken

    try:
        validate_password(new_password, user=user)
    except ValidationError as exc:
        raise InvalidNewPassword(exc.messages) from exc

    with transaction.atomic():
        user.set_password(new_password)
        user.save(update_fields=('password',))
        blacklist_user_refresh_tokens(user)

    return user


def change_password(*, user, old_password, new_password):
    if not user.check_password(old_password):
        raise InvalidOldPassword
    if user.check_password(new_password):
        raise InvalidNewPassword(
            ['Новый пароль должен отличаться от текущего.']
        )

    try:
        validate_password(new_password, user=user)
    except ValidationError as exc:
        raise InvalidNewPassword(exc.messages) from exc

    with transaction.atomic():
        user.set_password(new_password)
        user.save(update_fields=('password',))
        blacklist_user_refresh_tokens(user)

    return user

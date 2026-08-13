import math
import re
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import Profile, User
from draws.services.locks import lock_draw_operation
from promo.models import PromoCode, PromoCodeAttempt


CODE_PATTERN = re.compile(r'^[A-Z0-9]{8}$')
FAILURE_WINDOW = timedelta(minutes=1)
MAX_FAILURES = 3
BAN_DURATION = timedelta(minutes=5)


class PromoCodeRegistrationError(Exception):
    reason = ''
    message = ''

    def __init__(self, message=None):
        super().__init__(message or self.message)


class ProfileIncomplete(PromoCodeRegistrationError):
    reason = PromoCodeAttempt.Reason.PROFILE_INCOMPLETE
    message = 'Сначала заполните профиль.'


class InvalidPromoCodeFormat(PromoCodeRegistrationError):
    reason = PromoCodeAttempt.Reason.INVALID_FORMAT
    message = 'Промокод должен состоять из 8 цифр или латинских букв.'


class PromoCodeNotFound(PromoCodeRegistrationError):
    reason = PromoCodeAttempt.Reason.NOT_FOUND
    message = 'Такого промокода нет.'


class PromoCodeAlreadyRegistered(PromoCodeRegistrationError):
    reason = PromoCodeAttempt.Reason.ALREADY_REGISTERED
    message = 'Этот промокод уже зарегистрирован.'


class PromoCodeRateLimited(PromoCodeRegistrationError):
    reason = PromoCodeAttempt.Reason.RATE_LIMIT
    message = 'Слишком много неудачных попыток. Попробуйте позже.'

    def __init__(self, blocked_until, now):
        self.blocked_until = blocked_until
        self.retry_after = max(
            1,
            math.ceil((blocked_until - now).total_seconds()),
        )
        super().__init__()


def normalize_code(raw_code):
    return raw_code.strip().upper()


def _record_attempt(
    *,
    user,
    raw_code,
    normalized_code,
    result,
    reason,
    ip_address,
):
    return PromoCodeAttempt.objects.create(
        user=user,
        raw_code=raw_code[:64],
        normalized_code=(
            normalized_code if CODE_PATTERN.fullmatch(normalized_code) else ''
        ),
        result=result,
        reason=reason,
        ip_address=ip_address,
    )


def _active_ban(user, now):
    trigger = PromoCodeAttempt.objects.filter(
        user=user,
        result=PromoCodeAttempt.Result.BLOCKED,
        reason=PromoCodeAttempt.Reason.RATE_LIMIT,
        created_at__gt=now - BAN_DURATION,
    ).order_by('-created_at').first()
    if trigger is None:
        return None
    return trigger.created_at + BAN_DURATION


def get_registration_status(*, user):
    now = timezone.now()
    blocked_until = _active_ban(user, now)
    if blocked_until is None:
        return {
            'is_blocked': False,
            'retry_after': 0,
            'blocked_until': None,
        }

    return {
        'is_blocked': True,
        'retry_after': max(
            1,
            math.ceil((blocked_until - now).total_seconds()),
        ),
        'blocked_until': blocked_until,
    }


def _register_locked(*, user, raw_code, normalized_code, ip_address, now):
    profile = Profile.objects.filter(user=user).first()
    if profile is None or not profile.is_complete:
        _record_attempt(
            user=user,
            raw_code=raw_code,
            normalized_code=normalized_code,
            result=PromoCodeAttempt.Result.BLOCKED,
            reason=PromoCodeAttempt.Reason.PROFILE_INCOMPLETE,
            ip_address=ip_address,
        )
        return ProfileIncomplete()

    blocked_until = _active_ban(user, now)
    if blocked_until is not None:
        return PromoCodeRateLimited(blocked_until, now)

    recent_failures = PromoCodeAttempt.objects.filter(
        user=user,
        result=PromoCodeAttempt.Result.FAILURE,
        created_at__gt=now - FAILURE_WINDOW,
    ).count()
    if recent_failures >= MAX_FAILURES:
        attempt = _record_attempt(
            user=user,
            raw_code=raw_code,
            normalized_code=normalized_code,
            result=PromoCodeAttempt.Result.BLOCKED,
            reason=PromoCodeAttempt.Reason.RATE_LIMIT,
            ip_address=ip_address,
        )
        return PromoCodeRateLimited(
            attempt.created_at + BAN_DURATION,
            timezone.now(),
        )

    if not CODE_PATTERN.fullmatch(normalized_code):
        _record_attempt(
            user=user,
            raw_code=raw_code,
            normalized_code=normalized_code,
            result=PromoCodeAttempt.Result.FAILURE,
            reason=PromoCodeAttempt.Reason.INVALID_FORMAT,
            ip_address=ip_address,
        )
        return InvalidPromoCodeFormat()

    promo_code = (
        PromoCode.objects.select_for_update()
        .filter(code=normalized_code)
        .first()
    )
    if promo_code is None:
        _record_attempt(
            user=user,
            raw_code=raw_code,
            normalized_code=normalized_code,
            result=PromoCodeAttempt.Result.FAILURE,
            reason=PromoCodeAttempt.Reason.NOT_FOUND,
            ip_address=ip_address,
        )
        return PromoCodeNotFound()

    if promo_code.registered_by_id is not None:
        _record_attempt(
            user=user,
            raw_code=raw_code,
            normalized_code=normalized_code,
            result=PromoCodeAttempt.Result.FAILURE,
            reason=PromoCodeAttempt.Reason.ALREADY_REGISTERED,
            ip_address=ip_address,
        )
        return PromoCodeAlreadyRegistered()

    promo_code.registered_by = user
    promo_code.registered_at = now
    promo_code.save(update_fields=('registered_by', 'registered_at'))
    _record_attempt(
        user=user,
        raw_code=raw_code,
        normalized_code=normalized_code,
        result=PromoCodeAttempt.Result.SUCCESS,
        reason=PromoCodeAttempt.Reason.SUCCESS,
        ip_address=ip_address,
    )

    if profile.promo_code_email_notifications:
        from promo.services.notifications import schedule_registration_email

        transaction.on_commit(
            lambda: schedule_registration_email(promo_code.pk)
        )
    return promo_code


def register_promo_code(*, user, raw_code, ip_address=None):
    normalized_code = normalize_code(raw_code)

    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        now = timezone.now()
        lock_draw_operation(shared=True)
        now = timezone.now()
        result = _register_locked(
            user=locked_user,
            raw_code=raw_code,
            normalized_code=normalized_code,
            ip_address=ip_address,
            now=now,
        )

    if isinstance(result, PromoCodeRegistrationError):
        raise result
    return result

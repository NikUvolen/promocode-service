from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import Profile, User
from accounts.services.email_verification import schedule_verification_email


class EmailAlreadyRegistered(Exception):
    pass


class PersonalDataConsentRequired(Exception):
    pass


def register_user(*, email, password, personal_data_consent):
    if not personal_data_consent:
        raise PersonalDataConsentRequired

    normalized_email = User.objects.normalize_email(email).lower()
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=normalized_email,
                password=password,
            )
            Profile.objects.create(
                user=user,
                personal_data_consent_at=timezone.now(),
            )
    except IntegrityError as exc:
        raise EmailAlreadyRegistered from exc

    user.verification_email_queued = schedule_verification_email(user.pk)
    return user


def resend_verification_email(email):
    normalized_email = User.objects.normalize_email(email).lower()
    user = User.objects.filter(
        email=normalized_email,
        is_active=True,
        is_email_verified=False,
    ).first()
    if user is None:
        return True
    return schedule_verification_email(user.pk)

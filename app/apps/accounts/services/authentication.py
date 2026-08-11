from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Profile, User
from accounts.services.registration import PersonalDataConsentRequired


class InvalidCredentials(Exception):
    pass


class EmailNotVerified(Exception):
    pass


class InvalidRefreshToken(Exception):
    pass


def authenticate_user(*, request, email, password, personal_data_consent):
    if not personal_data_consent:
        raise PersonalDataConsentRequired

    normalized_email = User.objects.normalize_email(email).lower()
    user = authenticate(
        request=request,
        email=normalized_email,
        password=password,
    )
    if user is None:
        raise InvalidCredentials
    if not user.is_email_verified:
        raise EmailNotVerified

    profile, _ = Profile.objects.get_or_create(user=user)
    if profile.personal_data_consent_at is None:
        profile.personal_data_consent_at = timezone.now()
        profile.save(update_fields=('personal_data_consent_at', 'updated_at'))

    return user


def create_token_pair(user):
    refresh = RefreshToken.for_user(user)
    update_last_login(None, user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


def blacklist_refresh_token(token):
    try:
        RefreshToken(token).blacklist()
    except TokenError as exc:
        raise InvalidRefreshToken from exc

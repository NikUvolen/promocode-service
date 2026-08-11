from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User


class InvalidCredentials(Exception):
    pass


class EmailNotVerified(Exception):
    pass


class InvalidRefreshToken(Exception):
    pass


def authenticate_user(*, request, email, password):
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


def blacklist_user_refresh_tokens(user):
    outstanding_tokens = OutstandingToken.objects.filter(
        user=user,
        blacklistedtoken__isnull=True,
    )
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in outstanding_tokens],
        ignore_conflicts=True,
    )

from django.conf import settings


def set_auth_cookies(response, tokens):
    common = {
        'httponly': True,
        'secure': settings.JWT_COOKIE_SECURE,
        'samesite': settings.JWT_COOKIE_SAMESITE,
    }
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE_NAME,
        tokens['access'],
        max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        path='/api/v1/',
        **common,
    )
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        tokens['refresh'],
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        path='/api/v1/auth/',
        **common,
    )


def clear_auth_cookies(response):
    response.delete_cookie(
        settings.JWT_ACCESS_COOKIE_NAME,
        path='/api/v1/',
        samesite=settings.JWT_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        path='/api/v1/auth/',
        samesite=settings.JWT_COOKIE_SAMESITE,
    )

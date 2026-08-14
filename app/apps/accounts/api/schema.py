from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CookieJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = 'accounts.api.authentication.CookieJWTAuthentication'
    name = 'cookieAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'cookie',
            'name': settings.JWT_ACCESS_COOKIE_NAME,
            'description': 'JWT access-токен в HttpOnly cookie.',
        }

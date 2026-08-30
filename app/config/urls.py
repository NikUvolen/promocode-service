from django.contrib import admin
from django.conf import settings
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from redis import Redis
from redis.exceptions import RedisError


def healthcheck(request):
    checks = {'database': False, 'redis': False}

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        checks['database'] = True
    except DatabaseError:
        pass

    try:
        Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
        ).ping()
        checks['redis'] = True
    except RedisError:
        pass

    is_ready = all(checks.values())
    return JsonResponse(
        {
            'status': 'ok' if is_ready else 'unavailable',
            'checks': checks,
        },
        status=200 if is_ready else 503,
    )

urlpatterns = [
    path('health/', healthcheck, name='healthcheck'),
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path('api/v1/', include('accounts.api.urls')),
    path('api/v1/', include('promo.api.urls')),
    path('api/v1/', include('draws.api.urls')),
]

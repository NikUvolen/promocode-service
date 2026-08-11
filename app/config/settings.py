import sys
from datetime import timedelta
from pathlib import Path
from os import getenv

from dotenv import load_dotenv


load_dotenv()


def env_bool(name, default=False):
    return getenv(name, str(default)).lower() in {'1', 'true', 'yes', 'on'}

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / 'apps'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = getenv(
    'DJANGO_SECRET_KEY',
    'django-insecure-lgx-@3v+0qgrzaimps%=(fu+^-3c=$(8=ci@-oq0ngto&evvet',
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool('DJANGO_DEBUG', True)

ALLOWED_HOSTS = [
    host.strip()
    for host in getenv('DJANGO_ALLOWED_HOSTS', '').split(',')
    if host.strip()
]


# Application definition

INSTALLED_APPS = [
    'unfold',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'drf_spectacular_sidecar',

    'core',
    'accounts',
    'promo',
    'draws',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': getenv('DB_NAME', 'promocode_service'),
        'USER': getenv('DB_USER', 'postgres'),
        'PASSWORD': getenv('DB_PASSWORD', 'postgres'),
        'HOST': getenv('DB_HOST', 'localhost'),
        'PORT': getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': int(getenv('DB_CONN_MAX_AGE', '60')),
        'CONN_HEALTH_CHECKS': True,
    }
}


# Cache

REDIS_URL = getenv('REDIS_URL', 'redis://localhost:6379')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': getenv('CACHE_URL', f'{REDIS_URL}/1'),
    },
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'


# Email

EMAIL_BACKEND = getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(getenv('EMAIL_PORT', '25'))
EMAIL_HOST_USER = getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', False)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', False)
EMAIL_TIMEOUT = int(getenv('EMAIL_TIMEOUT', '10'))
DEFAULT_FROM_EMAIL = getenv('DEFAULT_FROM_EMAIL', 'noreply@example.com')
FRONTEND_URL = getenv('FRONTEND_URL', 'http://localhost:3000')
EMAIL_VERIFICATION_TIMEOUT = int(
    getenv('EMAIL_VERIFICATION_TIMEOUT', str(24 * 60 * 60))
)
PASSWORD_RESET_TIMEOUT = int(getenv('PASSWORD_RESET_TIMEOUT', '3600'))


# Celery

CELERY_BROKER_URL = getenv('CELERY_BROKER_URL', f'{REDIS_URL}/0')
CELERY_RESULT_BACKEND = getenv('CELERY_RESULT_BACKEND', f'{REDIS_URL}/2')
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ALWAYS_EAGER = env_bool('CELERY_TASK_ALWAYS_EAGER', False)
CELERY_TASK_EAGER_PROPAGATES = True

AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Промоакция API',
    'DESCRIPTION': 'API платформы регистрации промокодов и розыгрышей.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
}

UNFOLD = {
    'SITE_TITLE': 'Промоакция',
    'SITE_HEADER': 'Управление промоакцией',
    'SITE_SUBHEADER': 'Промокоды и ежедневные розыгрыши',
    'SITE_SYMBOL': 'redeem',
    'SHOW_HISTORY': True,
    'SHOW_VIEW_ON_SITE': False,
}

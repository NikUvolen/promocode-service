import sys
from datetime import timedelta
from pathlib import Path
from os import getenv

from celery.schedules import crontab
from django.urls import reverse_lazy
from dotenv import load_dotenv
from kombu import Queue


load_dotenv()


def env_bool(name, default=False):
    return getenv(name, str(default)).lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    return [value.strip() for value in getenv(name, default).split(',') if value.strip()]


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
IS_TESTING = 'test' in sys.argv
DJANGO_LOG_LEVEL = getenv('DJANGO_LOG_LEVEL', 'INFO')
APP_LOG_LEVEL = getenv('APP_LOG_LEVEL', 'INFO')
DJANGO_REQUEST_LOG_LEVEL = getenv(
    'DJANGO_REQUEST_LOG_LEVEL',
    'CRITICAL' if IS_TESTING else 'WARNING',
)

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

if not DEBUG and SECRET_KEY.startswith('django-insecure-'):
    raise RuntimeError('DJANGO_SECRET_KEY must be set in production.')


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
    'draws.apps.DrawsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if IS_TESTING:
    MIDDLEWARE.remove('whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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
TEST_RUNNER = 'config.test_runner.ProjectTestRunner'


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

CACHE_URL = getenv('CACHE_URL')
CACHES = {
    'default': (
        {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': CACHE_URL,
        }
        if CACHE_URL and not IS_TESTING
        else {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'promocode-service-local',
        }
    ),
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

if IS_TESTING:
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if IS_TESTING
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', False)
SECURE_REDIRECT_EXEMPT = [r'^health/$']
SESSION_COOKIE_SECURE = env_bool('DJANGO_SESSION_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_SECURE = env_bool('DJANGO_CSRF_COOKIE_SECURE', not DEBUG)
SECURE_HSTS_SECONDS = int(getenv('DJANGO_SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    'DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', False
)
SECURE_HSTS_PRELOAD = env_bool('DJANGO_SECURE_HSTS_PRELOAD', False)


# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': (
                '%(asctime)s %(levelname)s %(name)s '
                '%(process)d %(message)s'
            ),
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': APP_LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': DJANGO_LOG_LEVEL,
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': DJANGO_REQUEST_LOG_LEVEL,
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': APP_LOG_LEVEL,
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console'],
            'level': APP_LOG_LEVEL,
            'propagate': False,
        },
        'core': {
            'handlers': ['console'],
            'level': APP_LOG_LEVEL,
            'propagate': False,
        },
        'draws': {
            'handlers': ['console'],
            'level': APP_LOG_LEVEL,
            'propagate': False,
        },
        'promo': {
            'handlers': ['console'],
            'level': APP_LOG_LEVEL,
            'propagate': False,
        },
    },
}


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
PASSWORD_RESET_RESEND_INTERVAL = int(
    getenv('PASSWORD_RESET_RESEND_INTERVAL', '60')
)


# Celery

CELERY_BROKER_URL = (
    'memory://'
    if IS_TESTING
    else getenv('CELERY_BROKER_URL', f'{REDIS_URL}/0')
)
CELERY_RESULT_BACKEND = (
    'cache+memory://'
    if IS_TESTING
    else getenv('CELERY_RESULT_BACKEND', f'{REDIS_URL}/2')
)
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'socket_connect_timeout': 2,
    'socket_timeout': 5,
    # Bulk XLSX jobs may legitimately run longer than Redis' one-hour default.
    'visibility_timeout': int(
        getenv('CELERY_VISIBILITY_TIMEOUT', str(12 * 60 * 60))
    ),
}
CELERY_TASK_PUBLISH_RETRY = True
CELERY_TASK_PUBLISH_RETRY_POLICY = {
    'max_retries': 3,
    'interval_start': 0.2,
    'interval_step': 0.5,
    'interval_max': 2,
}
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ALWAYS_EAGER = IS_TESTING or env_bool(
    'CELERY_TASK_ALWAYS_EAGER',
    False,
)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_DEFAULT_QUEUE = 'maintenance'
CELERY_TASK_DEFAULT_EXCHANGE = 'maintenance'
CELERY_TASK_DEFAULT_EXCHANGE_TYPE = 'direct'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'maintenance'
CELERY_TASK_CREATE_MISSING_QUEUES = False
CELERY_WORKER_CANCEL_LONG_RUNNING_TASKS_ON_CONNECTION_LOSS = True
CELERY_TASK_QUEUES = (
    Queue('critical', exchange='critical', routing_key='critical'),
    Queue(
        'notifications',
        exchange='notifications',
        routing_key='notifications',
    ),
    Queue('generation', exchange='generation', routing_key='generation'),
    Queue('imports', exchange='imports', routing_key='imports'),
    Queue('reports', exchange='reports', routing_key='reports'),
    Queue(
        'maintenance',
        exchange='maintenance',
        routing_key='maintenance',
    ),
)
CELERY_TASK_ROUTES = {
    'draws.tasks.run_daily_draw_task': {'queue': 'critical'},
    'draws.tasks.run_manual_draw_task': {'queue': 'critical'},
    'accounts.tasks.send_verification_email_task': {
        'queue': 'notifications',
    },
    'accounts.tasks.send_password_reset_email_task': {
        'queue': 'notifications',
    },
    'promo.tasks.send_registration_email_task': {
        'queue': 'notifications',
    },
    'draws.tasks.send_winner_email_task': {'queue': 'notifications'},
    'draws.tasks.retry_unnotified_winner_emails_task': {
        'queue': 'notifications',
    },
    'promo.tasks.generate_promo_codes_task': {'queue': 'generation'},
    'promo.tasks.import_promo_codes_task': {'queue': 'imports'},
    'draws.tasks.generate_draw_report_task': {'queue': 'reports'},
    'promo.tasks.cleanup_expired_import_files_task': {
        'queue': 'maintenance',
    },
    'draws.tasks.cleanup_expired_report_files_task': {
        'queue': 'maintenance',
    },
    'core.tasks.cleanup_expired_audit_logs_task': {
        'queue': 'maintenance',
    },
    'core.tasks.fail_stale_background_jobs_task': {
        'queue': 'maintenance',
    },
}
CELERY_BEAT_SCHEDULE = {
    'run-daily-draw-at-moscow-midnight': {
        'task': 'draws.tasks.run_daily_draw_task',
        'schedule': crontab(hour=0, minute=0),
        'options': {'expires': 60 * 60},
    },
    'cleanup-expired-import-files': {
        'task': 'promo.tasks.cleanup_expired_import_files_task',
        'schedule': crontab(hour=3, minute=30),
        'options': {'expires': 60 * 60},
    },
    'retry-unnotified-winner-emails': {
        'task': 'draws.tasks.retry_unnotified_winner_emails_task',
        'schedule': crontab(minute='*/5'),
        'options': {'expires': 5 * 60},
    },
    'cleanup-expired-report-files': {
        'task': 'draws.tasks.cleanup_expired_report_files_task',
        'schedule': crontab(hour=3, minute=35),
        'options': {'expires': 60 * 60},
    },
    'cleanup-expired-audit-logs': {
        'task': 'core.tasks.cleanup_expired_audit_logs_task',
        'schedule': crontab(hour=3, minute=45),
        'options': {'expires': 60 * 60},
    },
    'fail-stale-background-jobs': {
        'task': 'core.tasks.fail_stale_background_jobs_task',
        'schedule': crontab(minute='*/15'),
        'options': {'expires': 15 * 60},
    },
}

XLSX_MAX_UPLOAD_SIZE = int(getenv('XLSX_MAX_UPLOAD_SIZE', str(20 * 1024 * 1024)))
GENERATED_FILE_RETENTION_DAYS = int(
    getenv('GENERATED_FILE_RETENTION_DAYS', '7')
)
AUDIT_LOG_RETENTION_DAYS = int(getenv('AUDIT_LOG_RETENTION_DAYS', '180'))
BACKGROUND_JOB_QUEUE_TIMEOUT = int(
    getenv('BACKGROUND_JOB_QUEUE_TIMEOUT', str(24 * 60 * 60))
)
BACKGROUND_JOB_RUNNING_TIMEOUT = int(
    getenv('BACKGROUND_JOB_RUNNING_TIMEOUT', str(6 * 60 * 60))
)
DRAW_CAMPAIGN_START_DATE = getenv('DRAW_CAMPAIGN_START_DATE', '')
LOAD_TEST_ALLOWED = env_bool('LOAD_TEST_ALLOWED', False)
PUBLIC_DRAWS_CACHE_TIMEOUT = int(
    getenv('PUBLIC_DRAWS_CACHE_TIMEOUT', str(5 * 60))
)

AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'accounts.api.authentication.CookieJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'core.exceptions.api_exception_handler',
    'DEFAULT_THROTTLE_RATES': {
        'auth_register': getenv('AUTH_REGISTER_RATE', '5/hour'),
        'auth_login': getenv('AUTH_LOGIN_RATE', '10/minute'),
        'auth_email': getenv('AUTH_EMAIL_RATE', '5/hour'),
        'auth_refresh': getenv('AUTH_REFRESH_RATE', '30/minute'),
        'promo_code_register': getenv('PROMO_CODE_REGISTER_RATE', '20/minute'),
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'CHECK_REVOKE_TOKEN': True,
}

JWT_ACCESS_COOKIE_NAME = getenv('JWT_ACCESS_COOKIE_NAME', 'gear_access')
JWT_REFRESH_COOKIE_NAME = getenv('JWT_REFRESH_COOKIE_NAME', 'gear_refresh')
JWT_COOKIE_SECURE = env_bool('JWT_COOKIE_SECURE', False)
JWT_COOKIE_SAMESITE = getenv('JWT_COOKIE_SAMESITE', 'Lax')

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
    'SITE_ICON': '/static/images/admin-favicon.png',
    'SITE_FAVICONS': [
        {
            'rel': 'icon',
            'href': '/static/images/admin-favicon.png',
            'type': 'image/png',
        },
    ],
    'SHOW_HISTORY': True,
    'SHOW_VIEW_ON_SITE': False,
    'SIDEBAR': {
        'navigation': [
            {
                'title': 'Промокоды',
                'items': [
                    {
                        'title': 'Промокоды',
                        'icon': 'confirmation_number',
                        'link': reverse_lazy(
                            'admin:promo_promocode_changelist',
                        ),
                    }
                ]
            },
            {
                'title': 'Розыгрыши',
                'items': [
                    {
                        'title': 'Розыгрыши',
                        'icon': 'casino',
                        'link': reverse_lazy(
                            'admin:draws_draw_changelist',
                        ),
                    },
                    {
                        'title': 'Победители',
                        'icon': 'emoji_events',
                        'link': reverse_lazy(
                            'admin:draws_winner_changelist',
                        ),
                    },
                    {
                        'title': 'Отчеты',
                        'icon': 'bar_chart',
                        'link': reverse_lazy(
                            'admin:draws_drawreport_changelist',
                        ),
                    }
                ]
            },
            {
                'title': 'Системное',
                'collapsible': True,
                'items': [
                    {
                        'title': 'Генерации промокодов',
                        'icon': 'event_note',
                        'link': reverse_lazy(
                            'admin:promo_promocodegeneration_changelist',
                        ),
                    },
                    {
                        'title': 'Импорт промокодов',
                        'icon': 'file_upload',
                        'link': reverse_lazy(
                            'admin:promo_promocodeimport_changelist',
                        ),
                    },
                    {
                        'title': 'Попытки ввода промокодов',
                        'icon': 'error',
                        'link': reverse_lazy(
                            'admin:promo_promocodeattempt_changelist',
                        ),
                    },
                    {
                        'title': 'Журнал аудита',
                        'icon': 'list',
                        'link': reverse_lazy(
                            'admin:core_auditlog_changelist'
                        ),
                    }
                ]
            },
            {
                'title': 'Администрирование',
                'collapsible': True,
                'items': [
                    {
                        'title': 'Пользователи',
                        'icon': 'person',
                        'link': reverse_lazy(
                            'admin:accounts_user_changelist'
                        ),
                    },
                    {
                        'title': 'Профили',
                        'icon': 'account_box',
                        'link': reverse_lazy(
                            'admin:accounts_profile_changelist'
                        ),
                    },
                    {
                        'title': 'Группы',
                        'icon': 'group',
                        'link': reverse_lazy(
                            'admin:auth_group_changelist'
                        ),
                    }
                ]
            }
        ],
    },
}

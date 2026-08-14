from django.conf import settings
from django.middleware.csrf import get_token
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from accounts.models import Profile
from accounts.services.authentication import (
    InvalidRefreshToken,
    blacklist_refresh_token,
)
from accounts.services.registration import resend_verification_email
from accounts.services.passwords import (
    EmailQueueUnavailable,
    PasswordResetRateLimited,
    request_password_reset,
)

from .serializers import (
    ChangePasswordSerializer,
    DetailResponseSerializer,
    LoginSerializer,
    LoginResponseSerializer,
    NotificationSettingsSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    RefreshSerializer,
    RegistrationResponseSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    SessionResponseSerializer,
    VerifyEmailSerializer,
)
from .authentication import CookieJWTAuthentication, enforce_csrf
from .cookies import clear_auth_cookies, set_auth_cookies


class AuthViewSet(viewsets.GenericViewSet):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_scope = None

    @extend_schema(
        tags=('Авторизация',),
        request=RegisterSerializer,
        responses={201: RegistrationResponseSerializer},
    )
    @action(
        detail=False,
        methods=('post',),
        throttle_classes=(ScopedRateThrottle,),
        throttle_scope='auth_register',
    )
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'email': user.email,
                'email_queued': user.verification_email_queued,
                'detail': (
                    'Письмо для подтверждения email поставлено в очередь.'
                    if user.verification_email_queued
                    else 'Аккаунт создан, но письмо пока не отправлено. '
                    'Запросите его повторно через минуту.'
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=('Авторизация',),
        request=VerifyEmailSerializer,
        responses={200: DetailResponseSerializer},
    )
    @action(detail=False, methods=('post',), url_path='verify-email')
    def verify_email(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Email подтвержден.'})

    @extend_schema(
        tags=('Авторизация',),
        request=ResendVerificationSerializer,
        responses={200: DetailResponseSerializer},
    )
    @action(
        detail=False,
        methods=('post',),
        url_path='resend-verification',
        throttle_classes=(ScopedRateThrottle,),
        throttle_scope='auth_email',
    )
    def resend_verification(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queued = resend_verification_email(serializer.validated_data['email'])
        if not queued:
            return Response(
                {'detail': 'Сервис отправки писем временно недоступен.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                'detail': (
                    'Если аккаунт существует и email не подтвержден, '
                    'письмо будет отправлено.'
                )
            }
        )

    @extend_schema(
        tags=('Авторизация',),
        request=PasswordResetRequestSerializer,
        responses={200: DetailResponseSerializer},
    )
    @action(
        detail=False,
        methods=('post',),
        url_path='password-reset',
        throttle_classes=(ScopedRateThrottle,),
        throttle_scope='auth_email',
    )
    def password_reset(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            request_password_reset(serializer.validated_data['email'])
        except PasswordResetRateLimited as exc:
            return Response(
                {
                    'detail': 'Повторить отправку можно через одну минуту.',
                    'retry_after': exc.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except EmailQueueUnavailable:
            return Response(
                {'detail': 'Сервис отправки писем временно недоступен.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                'detail': (
                    'Если аккаунт существует, письмо для восстановления '
                    'будет отправлено.'
                )
            }
        )

    @extend_schema(
        tags=('Авторизация',),
        request=PasswordResetConfirmSerializer,
        responses={200: DetailResponseSerializer},
    )
    @action(
        detail=False,
        methods=('post',),
        url_path='password-reset-confirm',
    )
    def password_reset_confirm(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Пароль изменен.'})

    @extend_schema(
        tags=('Авторизация',),
        request=ChangePasswordSerializer,
        responses={204: OpenApiResponse(description='Пароль изменен.')},
    )
    @action(
        detail=False,
        methods=('post',),
        url_path='change-password',
        authentication_classes=(CookieJWTAuthentication,),
        permission_classes=(IsAuthenticated,),
    )
    def change_password(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=('Профиль',),
        request=ProfileSerializer,
        responses={200: ProfileSerializer},
    )
    @action(
        detail=False,
        methods=('get', 'patch'),
        authentication_classes=(CookieJWTAuthentication,),
        permission_classes=(IsAuthenticated,),
    )
    def profile(self, request):
        profile, _ = Profile.objects.get_or_create(
            user=request.user,
        )
        if request.method == 'PATCH':
            serializer = ProfileSerializer(
                profile,
                data=request.data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    @extend_schema(
        tags=('Настройки',),
        request=NotificationSettingsSerializer,
        responses={200: NotificationSettingsSerializer},
    )
    @action(
        detail=False,
        methods=('get', 'patch'),
        url_path='notification-settings',
        authentication_classes=(CookieJWTAuthentication,),
        permission_classes=(IsAuthenticated,),
    )
    def notification_settings(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if request.method == 'PATCH':
            serializer = NotificationSettingsSerializer(
                profile,
                data=request.data,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            serializer = NotificationSettingsSerializer(profile)
        return Response(serializer.data)

    @extend_schema(
        tags=('Авторизация',),
        request=LoginSerializer,
        responses={200: LoginResponseSerializer},
    )
    @action(
        detail=False,
        methods=('post',),
        throttle_classes=(ScopedRateThrottle,),
        throttle_scope='auth_login',
    )
    def login(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        response = Response({'detail': 'Вход выполнен.'})
        set_auth_cookies(response, serializer.validated_data)
        return response

    @extend_schema(
        tags=('Авторизация',),
        responses={200: SessionResponseSerializer},
    )
    @action(
        detail=False,
        methods=('get',),
        authentication_classes=(CookieJWTAuthentication,),
    )
    def session(self, request):
        get_token(request)
        return Response({'authenticated': request.user.is_authenticated})

    @extend_schema(
        tags=('Авторизация',),
        request=None,
        responses={200: DetailResponseSerializer},
    )
    @action(
        detail=False,
        methods=('post',),
        throttle_classes=(ScopedRateThrottle,),
        throttle_scope='auth_refresh',
    )
    def refresh(self, request):
        enforce_csrf(request)
        refresh_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        serializer = RefreshSerializer(data={'refresh': refresh_token})
        serializer.is_valid(raise_exception=True)
        response = Response({'detail': 'Сессия обновлена.'})
        set_auth_cookies(response, serializer.validated_data)
        return response

    @extend_schema(
        tags=('Авторизация',),
        request=None,
        responses={204: OpenApiResponse(description='Выход выполнен.')},
    )
    @action(detail=False, methods=('post',))
    def logout(self, request):
        enforce_csrf(request)
        refresh_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if refresh_token:
            try:
                blacklist_refresh_token(refresh_token)
            except InvalidRefreshToken:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response)
        return response

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.services.registration import resend_verification_email
from accounts.services.passwords import request_password_reset

from .serializers import (
    ChangePasswordSerializer,
    DetailResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RefreshSerializer,
    RegistrationResponseSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    TokenPairResponseSerializer,
    VerifyEmailSerializer,
)


class AuthViewSet(viewsets.GenericViewSet):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=('Авторизация',),
        request=RegisterSerializer,
        responses={201: RegistrationResponseSerializer},
    )
    @action(detail=False, methods=('post',))
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'email': user.email,
                'detail': 'Письмо для подтверждения email отправлено.',
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
    )
    def resend_verification(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resend_verification_email(serializer.validated_data['email'])
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
    @action(detail=False, methods=('post',), url_path='password-reset')
    def password_reset(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(serializer.validated_data['email'])
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
        authentication_classes=(JWTAuthentication,),
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
        tags=('Авторизация',),
        request=LoginSerializer,
        responses={200: TokenPairResponseSerializer},
    )
    @action(detail=False, methods=('post',))
    def login(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)

    @extend_schema(
        tags=('Авторизация',),
        request=RefreshSerializer,
        responses={200: TokenPairResponseSerializer},
    )
    @action(detail=False, methods=('post',))
    def refresh(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)

    @extend_schema(
        tags=('Авторизация',),
        request=LogoutSerializer,
        responses={204: OpenApiResponse(description='Выход выполнен.')},
    )
    @action(detail=False, methods=('post',))
    def logout(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

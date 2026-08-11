from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.services.registration import resend_verification_email

from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    RefreshSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    VerifyEmailSerializer,
)


class AuthViewSet(viewsets.GenericViewSet):
    authentication_classes = ()
    permission_classes = (AllowAny,)

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

    @action(detail=False, methods=('post',), url_path='verify-email')
    def verify_email(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Email подтвержден.'})

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

    @action(detail=False, methods=('post',))
    def login(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)

    @action(detail=False, methods=('post',))
    def refresh(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)

    @action(detail=False, methods=('post',))
    def logout(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

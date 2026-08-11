from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from accounts.models import User
from accounts.services.authentication import (
    EmailNotVerified,
    InvalidCredentials,
    InvalidRefreshToken,
    authenticate_user,
    blacklist_refresh_token,
    create_token_pair,
)
from accounts.services.email_verification import (
    InvalidEmailVerificationToken,
    verify_email,
)
from accounts.services.registration import (
    EmailAlreadyRegistered,
    PersonalDataConsentRequired,
    register_user,
)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    personal_data_consent = serializers.BooleanField(write_only=True)

    def validate_email(self, value):
        email = User.objects.normalize_email(value).lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                'Пользователь с таким email уже зарегистрирован.'
            )
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_personal_data_consent(self, value):
        if not value:
            raise serializers.ValidationError(
                'Необходимо согласие на обработку персональных данных.'
            )
        return value

    def create(self, validated_data):
        try:
            return register_user(**validated_data)
        except EmailAlreadyRegistered as exc:
            raise serializers.ValidationError(
                {'email': 'Пользователь с таким email уже зарегистрирован.'}
            ) from exc
        except PersonalDataConsentRequired as exc:
            raise serializers.ValidationError(
                {
                    'personal_data_consent': (
                        'Необходимо согласие на обработку персональных данных.'
                    )
                }
            ) from exc


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField(trim_whitespace=False)

    def save(self, **kwargs):
        try:
            return verify_email(self.validated_data['token'])
        except InvalidEmailVerificationToken as exc:
            raise serializers.ValidationError(
                {'token': 'Ссылка недействительна или устарела.'}
            ) from exc


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    personal_data_consent = serializers.BooleanField(write_only=True)

    def validate(self, attrs):
        try:
            user = authenticate_user(
                request=self.context.get('request'),
                **attrs,
            )
        except InvalidCredentials as exc:
            raise serializers.ValidationError(
                'Неверный email или пароль.'
            ) from exc
        except EmailNotVerified as exc:
            raise serializers.ValidationError(
                'Сначала подтвердите email.'
            ) from exc
        except PersonalDataConsentRequired as exc:
            raise serializers.ValidationError(
                {
                    'personal_data_consent': (
                        'Необходимо согласие на обработку персональных данных.'
                    )
                }
            ) from exc

        return create_token_pair(user)


class RefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except TokenError as exc:
            raise serializers.ValidationError(
                {'refresh': 'Refresh-токен недействителен.'}
            ) from exc


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True, trim_whitespace=False)

    def save(self, **kwargs):
        try:
            blacklist_refresh_token(self.validated_data['refresh'])
        except InvalidRefreshToken as exc:
            raise serializers.ValidationError(
                {'refresh': 'Refresh-токен недействителен.'}
            ) from exc

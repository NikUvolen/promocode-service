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
from accounts.services.passwords import (
    InvalidNewPassword,
    InvalidOldPassword,
    InvalidPasswordResetToken,
    change_password,
    reset_password,
)
from accounts.services.profile import (
    normalize_phone,
    update_notification_settings,
    update_profile,
)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
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

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {'confirm_password': 'Пароли не совпадают.'}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
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


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(trim_whitespace=False)
    token = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def save(self, **kwargs):
        try:
            return reset_password(**self.validated_data)
        except InvalidPasswordResetToken as exc:
            raise serializers.ValidationError(
                {'token': 'Ссылка недействительна или устарела.'}
            ) from exc
        except InvalidNewPassword as exc:
            raise serializers.ValidationError(
                {'new_password': exc.messages}
            ) from exc


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def save(self, **kwargs):
        try:
            return change_password(
                user=self.context['request'].user,
                **self.validated_data,
            )
        except InvalidOldPassword as exc:
            raise serializers.ValidationError(
                {'old_password': 'Текущий пароль указан неверно.'}
            ) from exc
        except InvalidNewPassword as exc:
            raise serializers.ValidationError(
                {'new_password': exc.messages}
            ) from exc


class ProfileSerializer(serializers.Serializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(max_length=100, allow_blank=True)
    last_name = serializers.CharField(max_length=100, allow_blank=True)
    middle_name = serializers.CharField(
        max_length=100,
        allow_blank=True,
        required=False,
    )
    no_middle_name = serializers.BooleanField()
    phone = serializers.CharField(max_length=32, allow_blank=True)
    is_complete = serializers.BooleanField(read_only=True)

    def validate(self, attrs):
        instance = self.instance
        values = {
            'first_name': attrs.get('first_name', instance.first_name),
            'last_name': attrs.get('last_name', instance.last_name),
            'middle_name': attrs.get('middle_name', instance.middle_name),
            'no_middle_name': attrs.get(
                'no_middle_name',
                instance.no_middle_name,
            ),
            'phone': attrs.get('phone', instance.phone),
        }

        for field in ('first_name', 'last_name', 'middle_name', 'phone'):
            values[field] = values[field].strip()

        errors = {}
        for field in ('first_name', 'last_name', 'phone'):
            if not values[field]:
                errors[field] = 'Обязательное поле.'

        if not values['no_middle_name'] and not values['middle_name']:
            errors['middle_name'] = (
                'Укажите отчество или отметьте, что его нет.'
            )

        if values['phone']:
            try:
                values['phone'] = normalize_phone(values['phone'])
            except ValueError:
                errors['phone'] = 'Введите российский номер из 10 цифр.'

        if errors:
            raise serializers.ValidationError(errors)

        attrs.update(values)
        return attrs

    def update(self, instance, validated_data):
        return update_profile(profile=instance, **validated_data)


class NotificationSettingsSerializer(serializers.Serializer):
    promo_code_email_notifications = serializers.BooleanField()

    def update(self, instance, validated_data):
        return update_notification_settings(
            profile=instance,
            **validated_data,
        )


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class RegistrationResponseSerializer(DetailResponseSerializer):
    email = serializers.EmailField()
    email_queued = serializers.BooleanField()


class TokenPairResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()

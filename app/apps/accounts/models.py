from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.conf import settings


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        return self.get(email__iexact=self.normalize_email(username))

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Необходимо указать email пользователя.')

        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('У суперпользователя должен быть установлен is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('У суперпользователя должен быть установлен is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    first_name = None
    last_name = None

    email = models.EmailField('email', unique=True)
    is_email_verified = models.BooleanField('email подтверждён', default=False)

    objects = UserManager()  # type: ignore[assignment]

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email).lower()

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'пользователи'


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='пользователь',
    )

    first_name = models.CharField(
        'имя',
        max_length=100,
        blank=True,
    )
    last_name = models.CharField(
        'фамилия',
        max_length=100,
        blank=True,
    )
    middle_name = models.CharField(
        'отчество',
        max_length=100,
        blank=True,
    )
    no_middle_name = models.BooleanField(
        'нет отчества',
        default=False,
    )
    phone = models.CharField(
        'телефон',
        max_length=32,
        blank=True,
    )
    personal_data_consent_at = models.DateTimeField(
        'согласие на обработку данных получено',
        blank=True,
        null=True,
    )
    promo_code_email_notifications = models.BooleanField(
        'письма о регистрации промокода',
        default=True,
    )

    created_at = models.DateTimeField(
        'создан',
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        'обновлён',
        auto_now=True,
    )

    def __str__(self):
        return f'{self.first_name} {self.last_name} | {self.user.email}'

    class Meta:
        verbose_name = 'профиль'
        verbose_name_plural = 'профили'
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(no_middle_name=False)
                    | models.Q(middle_name='')
                ),
                name='profile_no_middle_name_consistent',
            ),
        ]

    @property
    def is_complete(self):
        middle_name: str = self.middle_name or ''
        has_middle_name = self.no_middle_name or bool(middle_name.strip())

        return all([
            self.first_name.strip(),
            self.last_name.strip(),
            self.phone.strip(),
            has_middle_name,
        ])

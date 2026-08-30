from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class PromoCode(models.Model):
    code = models.CharField(
        'промокод',
        max_length=8,
        unique=True,
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promo_codes',
        verbose_name='зарегистрировал',
    )
    registered_at = models.DateTimeField(
        'дата регистрации',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        'дата создания',
        auto_now_add=True,
    )

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        code_is_being_updated = update_fields is None or 'code' in update_fields

        if self.pk and code_is_being_updated:
            original_code = (
                type(self).objects.filter(pk=self.pk)
                .values_list('code', flat=True)
                .first()
            )
            if original_code is not None and self.code != original_code:
                raise ValidationError(
                    {'code': 'Промокод нельзя изменить после создания.'},
                )

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = 'промокод'
        verbose_name_plural = 'промокоды'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__regex=r'^[A-Z0-9]{8}$'),
                name='promo_code_format_valid',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        registered_by__isnull=True,
                        registered_at__isnull=True,
                    )
                    | models.Q(
                        registered_by__isnull=False,
                        registered_at__isnull=False,
                    )
                ),
                name='promo_code_registration_consistent',
            ),
        ]
        indexes = [
            models.Index(fields=['registered_at']),
            models.Index(fields=['registered_by']),
        ]


class PromoCodeAttempt(models.Model):
    class Result(models.TextChoices):
        SUCCESS = 'success', 'Успешно'
        FAILURE = 'failed', 'Ошибка'
        BLOCKED = 'blocked', 'Заблокировано'

    class Reason(models.TextChoices):
        SUCCESS = 'success', 'Успешная регистрация'
        INVALID_FORMAT = 'invalid_format', 'Неверный формат'
        NOT_FOUND = 'not_found', 'Код не найден'
        ALREADY_REGISTERED = 'already_registered', 'Код уже зарегистрирован'
        PROFILE_INCOMPLETE = 'profile_incomplete', 'Профиль не заполнен'
        RATE_LIMIT = 'rate_limited', 'Превышен лимит попыток'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='promo_code_attempts',
        verbose_name='пользователь',
    )
    raw_code = models.CharField(
        'введённое значение',
        max_length=64,
    )
    normalized_code = models.CharField(
        'нормализованный код',
        max_length=8,
        blank=True,
    )
    result = models.CharField(
        'результат',
        max_length=16,
        choices=Result.choices,
    )
    reason = models.CharField(
        'причина',
        max_length=32,
        choices=Reason.choices,
    )
    created_at = models.DateTimeField(
        'дата попытки',
        auto_now_add=True,
    )
    def __str__(self):
        return f'{self.user.pk} | {self.normalized_code} | {self.result}'

    class Meta:
        verbose_name = 'попытка ввода промокода'
        verbose_name_plural = 'попытки ввода промокодов'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['normalized_code']),
            models.Index(fields=['result', 'created_at']),
        ]


class PromoCodeGeneration(models.Model):
    class Status(models.TextChoices):
        QUEUED = 'queued', 'В очереди'
        RUNNING = 'running', 'Выполняется'
        COMPLETED = 'completed', 'Завершено'
        FAILED = 'failed', 'Ошибка'

    requested_count = models.PositiveIntegerField('запрошено кодов')
    generated_count = models.PositiveIntegerField('сгенерировано кодов', default=0)
    status = models.CharField(
        'статус',
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='promo_code_generations',
        verbose_name='запустил',
    )
    celery_task_id = models.CharField('ID задачи Celery', max_length=255, blank=True)
    error = models.TextField('ошибка', blank=True)
    lock_key = models.CharField(
        max_length=32,
        default='promo_codes',
        editable=False,
    )
    created_at = models.DateTimeField('создана', auto_now_add=True)
    started_at = models.DateTimeField('начата', null=True, blank=True)
    finished_at = models.DateTimeField('завершена', null=True, blank=True)

    def __str__(self):
        return f'{self.requested_count} кодов | {self.get_status_display()}'

    @property
    def progress_percent(self):
        if not self.requested_count:
            return 0
        return min(100, self.generated_count * 100 // self.requested_count)

    class Meta:
        verbose_name = 'генерация промокодов'
        verbose_name_plural = 'генерации промокодов'
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=['lock_key'],
                condition=models.Q(status__in=['queued', 'running']),
                name='unique_active_promo_code_generation',
            ),
        ]


class PromoCodeImport(models.Model):
    class Status(models.TextChoices):
        QUEUED = 'queued', 'В очереди'
        RUNNING = 'running', 'Выполняется'
        COMPLETED = 'completed', 'Завершено'
        FAILED = 'failed', 'Ошибка'

    source_file = models.FileField('исходный файл', upload_to='promo_imports/source/%Y/%m/%d')
    original_filename = models.CharField('имя исходного файла', max_length=255)
    error_file = models.FileField(
        'файл с пропущенными строками',
        upload_to='promo_imports/errors/%Y/%m/%d',
        blank=True,
    )
    status = models.CharField(
        'статус',
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    processed_count = models.PositiveIntegerField('обработано строк', default=0)
    imported_count = models.PositiveIntegerField('импортировано кодов', default=0)
    skipped_count = models.PositiveIntegerField('пропущено строк', default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='promo_code_imports',
        verbose_name='загрузил',
    )
    celery_task_id = models.CharField('ID задачи Celery', max_length=255, blank=True)
    error = models.TextField('ошибка', blank=True)
    created_at = models.DateTimeField('создан', auto_now_add=True)
    started_at = models.DateTimeField('начат', null=True, blank=True)
    finished_at = models.DateTimeField('завершён', null=True, blank=True)

    def __str__(self):
        return f'{self.original_filename} | {self.get_status_display()}'

    class Meta:
        verbose_name = 'импорт промокодов'
        verbose_name_plural = 'импорты промокодов'
        ordering = ('-created_at',)

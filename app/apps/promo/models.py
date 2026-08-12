from django.db import models
from django.conf import settings


class PromoCode(models.Model):
    code = models.CharField(
        max_length=8,
        unique=True,
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promo_codes',
    )
    registered_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = 'promo code'
        verbose_name_plural = 'promo codes'
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
        SUCCESS = 'success', 'Success'
        FAILURE = 'failed', 'Failed'
        BLOCKED = 'blocked', 'Blocked'

    class Reason(models.TextChoices):
        SUCCESS = 'success', 'Success'
        INVALID_FORMAT = 'invalid_format', 'Invalid format'
        NOT_FOUND = 'not_found', 'Not found'
        ALREADY_REGISTERED = 'already_registered', 'Already registered'
        PROFILE_INCOMPLETE = 'profile_incomplete', 'Profile incomplete'
        RATE_LIMIT = 'rate_limited', 'Rate limited'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='promo_code_attempts',
    )
    raw_code = models.CharField(
        max_length=64,
    )
    normalized_code = models.CharField(
        max_length=8,
        blank=True,
    )
    result = models.CharField(
        max_length=16,
        choices=Result.choices,
    )
    reason = models.CharField(
        max_length=32,
        choices=Reason.choices,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f'{self.user.pk} | {self.normalized_code} | {self.result}'

    class Meta:
        verbose_name = 'promo code attempt'
        verbose_name_plural = 'promo code attempts'
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

    requested_count = models.PositiveIntegerField()
    generated_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='promo_code_generations',
    )
    celery_task_id = models.CharField(max_length=255, blank=True)
    error = models.TextField(blank=True)
    lock_key = models.CharField(
        max_length=32,
        default='promo_codes',
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.requested_count} codes | {self.get_status_display()}'

    @property
    def progress_percent(self):
        if not self.requested_count:
            return 0
        return min(100, self.generated_count * 100 // self.requested_count)

    class Meta:
        verbose_name = 'promo code generation'
        verbose_name_plural = 'promo code generations'
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=['lock_key'],
                condition=models.Q(status__in=['queued', 'running']),
                name='unique_active_promo_code_generation',
            ),
        ]

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class EventType(models.TextChoices):
        PROMO_GENERATION_QUEUED = (
            'promo_generation_queued',
            'Генерация кодов поставлена в очередь',
        )
        PROMO_GENERATION_STARTED = (
            'promo_generation_started',
            'Генерация кодов началась',
        )
        PROMO_GENERATION_COMPLETED = (
            'promo_generation_completed',
            'Генерация кодов завершена',
        )
        PROMO_GENERATION_FAILED = (
            'promo_generation_failed',
            'Генерация кодов завершилась ошибкой',
        )
        PROMO_IMPORT_QUEUED = (
            'promo_import_queued',
            'Импорт кодов поставлен в очередь',
        )
        PROMO_IMPORT_STARTED = (
            'promo_import_started',
            'Импорт кодов начался',
        )
        PROMO_IMPORT_COMPLETED = (
            'promo_import_completed',
            'Импорт кодов завершён',
        )
        PROMO_IMPORT_FAILED = (
            'promo_import_failed',
            'Импорт кодов завершился ошибкой',
        )
        DRAW_QUEUED = (
            'draw_queued',
            'Розыгрыш поставлен в очередь',
        )
        DRAW_COMPLETED = (
            'draw_completed',
            'Розыгрыш завершён',
        )
        DRAW_FAILED = (
            'draw_failed',
            'Розыгрыш завершился ошибкой',
        )
        DRAW_REPORT_QUEUED = (
            'draw_report_queued',
            'Отчёт поставлен в очередь',
        )
        DRAW_REPORT_STARTED = (
            'draw_report_started',
            'Формирование отчёта началось',
        )
        DRAW_REPORT_COMPLETED = (
            'draw_report_completed',
            'Формирование отчёта завершено',
        )
        DRAW_REPORT_FAILED = (
            'draw_report_failed',
            'Формирование отчёта завершилось ошибкой',
        )
        AUDIT_CLEANUP_COMPLETED = (
            'audit_cleanup_completed',
            'Очистка аудита завершена',
        )

    event_type = models.CharField(
        'событие',
        max_length=64,
        choices=EventType.choices,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='инициатор',
    )
    target_model = models.CharField('модель объекта', max_length=128, blank=True)
    target_object_id = models.CharField('ID объекта', max_length=64, blank=True)
    metadata = models.JSONField('дополнительные данные', default=dict, blank=True)
    created_at = models.DateTimeField('дата события', auto_now_add=True)

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M:%S} | {self.event_type}'

    class Meta:
        verbose_name = 'событие аудита'
        verbose_name_plural = 'журнал аудита'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('event_type', 'created_at')),
            models.Index(fields=('actor', 'created_at')),
            models.Index(fields=('target_model', 'target_object_id')),
        ]

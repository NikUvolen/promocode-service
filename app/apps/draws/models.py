from django.conf import settings
from django.db import models


class Draw(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает запуска'
        RUNNING = 'running', 'Выполняется'
        COMPLETED = 'completed', 'Завершён'
        FAILED = 'failed', 'Ошибка'

    class Trigger(models.TextChoices):
        AUTOMATIC = 'automatic', 'Автоматический'
        MANUAL = 'manual', 'Ручной'

    draw_date = models.DateField('дата розыгрыша', unique=True)
    status = models.CharField(
        'статус',
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    trigger = models.CharField(
        'способ запуска',
        max_length=16,
        choices=Trigger.choices,
        default=Trigger.AUTOMATIC,
    )
    started_at = models.DateTimeField('начат', null=True, blank=True)
    completed_at = models.DateTimeField('завершён', null=True, blank=True)
    period_started_at = models.DateTimeField('начало периода кодов', null=True, blank=True)
    period_ended_at = models.DateTimeField('конец периода кодов', null=True, blank=True)
    created_at = models.DateTimeField('создан', auto_now_add=True)
    updated_at = models.DateTimeField('обновлён', auto_now=True)

    def __str__(self):
        return f'{self.draw_date} | {self.status}'

    class Meta:
        verbose_name = 'розыгрыш'
        verbose_name_plural = 'розыгрыши'
        ordering = ['-draw_date']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=('pending', 'running', 'completed', 'failed')
                ),
                name='draw_status_valid',
            ),
            models.CheckConstraint(
                condition=models.Q(trigger__in=('automatic', 'manual')),
                name='draw_trigger_valid',
            ),
        ]
        permissions = [
            ('run_draw', 'Может проводить ручной розыгрыш'),
        ]


class Winner(models.Model):
    class Prize(models.TextChoices):
        OZON_3000 = 'ozon_3000', 'Сертификат Ozon на 3 000 рублей'
        AIRPODS = 'airpods', 'Наушники AirPods'

    draw = models.ForeignKey(
        Draw,
        on_delete=models.PROTECT,
        related_name='winners',
        verbose_name='розыгрыш',
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='wins',
        verbose_name='победитель',
    )
    promo_code = models.OneToOneField(
        'promo.PromoCode',
        on_delete=models.PROTECT,
        related_name='winner',
        verbose_name='промокод',
    )
    prize = models.CharField(
        'приз',
        max_length=32,
        choices=Prize.choices,
    )

    won_at = models.DateTimeField(
        'дата победы',
        auto_now_add=True,
    )
    notified_at = models.DateTimeField(
        'письмо отправлено',
        null=True,
        blank=True,
    )

    def __str__(self):
        return f'{self.draw.draw_date} | {self.user.pk} | {self.prize}'

    class Meta:
        verbose_name = 'победитель'
        verbose_name_plural = 'победители'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(prize__in=('ozon_3000', 'airpods')),
                name='winner_prize_valid',
            ),
            models.UniqueConstraint(
                fields=['user'],
                name='unique_winner_user',
            ),
            models.UniqueConstraint(
                fields=['draw', 'prize'],
                name='unique_prize_per_draw',
            ),
        ]
        ordering = ['-won_at']


class DrawReport(models.Model):
    class Status(models.TextChoices):
        QUEUED = 'queued', 'В очереди'
        RUNNING = 'running', 'Выполняется'
        COMPLETED = 'completed', 'Завершено'
        FAILED = 'failed', 'Ошибка'

    date_from = models.DateField('дата начала', null=True, blank=True)
    date_to = models.DateField('дата окончания', null=True, blank=True)
    report_file = models.FileField(
        'файл отчёта',
        upload_to='draw_reports/%Y/%m/%d',
        blank=True,
    )
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
        related_name='draw_reports',
        verbose_name='сформировал',
    )
    celery_task_id = models.CharField('ID задачи Celery', max_length=255, blank=True)
    error = models.TextField('ошибка', blank=True)
    created_at = models.DateTimeField('создан', auto_now_add=True)
    started_at = models.DateTimeField('начат', null=True, blank=True)
    finished_at = models.DateTimeField('завершён', null=True, blank=True)

    def __str__(self):
        date_from = self.date_from or 'начало акции'
        date_to = self.date_to or 'текущая дата'
        return f'{date_from} - {date_to} | {self.get_status_display()}'

    class Meta:
        verbose_name = 'отчёт по розыгрышам'
        verbose_name_plural = 'отчёты по розыгрышам'
        ordering = ('-created_at',)

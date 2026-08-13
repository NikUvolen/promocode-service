from django.conf import settings
from django.db import models


class Draw(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    class Trigger(models.TextChoices):
        AUTOMATIC = 'automatic', 'Automatic'
        MANUAL = 'manual', 'Manual'

    draw_date = models.DateField(unique=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    trigger = models.CharField(
        max_length=16,
        choices=Trigger.choices,
        default=Trigger.AUTOMATIC,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    period_started_at = models.DateTimeField(null=True, blank=True)
    period_ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.draw_date} | {self.status}'

    class Meta:
        verbose_name = 'draw'
        verbose_name_plural = 'draws'
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


class Winner(models.Model):
    class Prize(models.TextChoices):
        OZON_3000 = 'ozon_3000', 'Ozon 3000'
        AIRPODS = 'airpods', 'AirPods'

    draw = models.ForeignKey(
        Draw,
        on_delete=models.PROTECT,
        related_name='winners',
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='wins',
    )
    promo_code = models.OneToOneField(
        'promo.PromoCode',
        on_delete=models.PROTECT,
        related_name='winner',
    )
    prize = models.CharField(
        max_length=32,
        choices=Prize.choices,
    )

    won_at = models.DateTimeField(
        auto_now_add=True,
    )
    notified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f'{self.draw.draw_date} | {self.user.pk} | {self.prize}'

    class Meta:
        verbose_name = 'winner'
        verbose_name_plural = 'winners'
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

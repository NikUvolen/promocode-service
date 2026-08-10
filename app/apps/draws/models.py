from django.conf import settings
from django.db import models


class Winner(models.Model):
    class Prize(models.TextChoices):
        OZON_1500 = 'ozon_1500', 'Ozon 1500'
        OZON_3000 = 'ozon_3000', 'Ozon 3000'
        OZON_5000 = 'ozon_5000', 'Ozon 5000'

    draw_date = models.DateField()

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
        return f'{self.draw_date} | {self.user.pk} | {self.prize}'

    class Meta:
        verbose_name = 'winner'
        verbose_name_plural = 'winners'
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                name='unique_winner_user',
            ),
            models.UniqueConstraint(
                fields=['draw_date', 'prize'],
                name='unique_prize_per_draw_date',
            ),
        ]
        indexes = [
            models.Index(fields=['draw_date']),
        ]

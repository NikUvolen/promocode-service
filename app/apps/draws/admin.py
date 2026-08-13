from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from unfold.enums import ActionVariant

from .models import Draw, Winner
from .tasks import run_manual_draw_task


class WinnerInline(TabularInline):
    model = Winner
    extra = 0
    can_delete = False
    fields = ('user', 'promo_code', 'prize', 'won_at', 'notified_at')
    readonly_fields = fields
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Draw)
class DrawAdmin(ModelAdmin):
    actions_list = ('run_manual_draw',)
    list_display = (
        'draw_date',
        'status',
        'trigger',
        'started_at',
        'completed_at',
        'period_started_at',
        'period_ended_at',
    )
    list_filter = ('status', 'trigger', 'draw_date')
    search_fields = ('draw_date',)
    readonly_fields = (
        'draw_date',
        'status',
        'trigger',
        'started_at',
        'completed_at',
        'period_started_at',
        'period_ended_at',
        'created_at',
        'updated_at',
    )
    date_hierarchy = 'draw_date'
    inlines = (WinnerInline,)

    @action(
        description='Провести розыгрыш',
        icon='casino',
        permissions=('view',),
        variant=ActionVariant.PRIMARY,
        dialog={
            'title': 'Провести розыгрыш сейчас?',
            'description': (
                'В розыгрыш попадут промокоды, зарегистрированные после '
                'предыдущего розыгрыша и до момента запуска. Повторный '
                'запуск за эту дату не изменит победителей.'
            ),
            'form_submit_text': 'Запустить',
        },
    )
    def run_manual_draw(self, request, form):
        campaign_timezone = ZoneInfo(settings.TIME_ZONE)
        cutoff = timezone.now()
        draw_date = cutoff.astimezone(campaign_timezone).date()

        try:
            task = run_manual_draw_task.delay(
                draw_date.isoformat(),
                cutoff.isoformat(),
            )
        except Exception:
            messages.error(
                request,
                'Не удалось отправить задачу в Celery. Проверьте Redis и worker.',
            )
        else:
            messages.success(
                request,
                f'Розыгрыш поставлен в очередь. ID задачи: {task.id}.',
            )
        return redirect('admin:draws_draw_changelist')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Winner)
class WinnerAdmin(ModelAdmin):
    list_display = (
        'user',
        'draw_date',
        'prize',
        'promo_code',
        'won_at',
        'notified_at',
    )
    list_filter = ('prize', 'draw__draw_date', 'notified_at')
    search_fields = ('user__email', 'promo_code__code')
    readonly_fields = (
        'draw',
        'user',
        'promo_code',
        'prize',
        'won_at',
        'notified_at',
    )
    list_select_related = ('draw', 'user', 'promo_code')
    date_hierarchy = 'won_at'
    ordering = ('-won_at',)

    @admin.display(ordering='draw__draw_date', description='Дата розыгрыша')
    def draw_date(self, obj):
        return obj.draw.draw_date

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

from django.contrib import admin, messages
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.utils import timezone
from unfold.decorators import action
from unfold.enums import ActionVariant
from unfold.admin import ModelAdmin

from .forms import PromoCodeGenerationForm
from .models import PromoCode, PromoCodeAttempt, PromoCodeGeneration
from .tasks import generate_promo_codes_task


@admin.register(PromoCode)
class PromoCodeAdmin(ModelAdmin):
    actions_list = ('generate_codes',)
    list_before_template = 'admin/promo/promocode/generation_status.html'
    list_display = ('code', 'is_registered', 'registered_by', 'registered_at')
    list_filter = (
        ('registered_by', admin.EmptyFieldListFilter),
        ('registered_at', admin.DateFieldListFilter),
    )
    search_fields = ('code', 'registered_by__email')
    autocomplete_fields = ('registered_by',)
    readonly_fields = ('registered_by', 'registered_at', 'created_at')
    list_select_related = ('registered_by',)
    date_hierarchy = 'registered_at'
    ordering = ('code',)
    list_per_page = 100

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(
            {
                'promo_code_count': PromoCode.objects.count(),
                'latest_generation': PromoCodeGeneration.objects.first(),
            }
        )
        return super().changelist_view(request, extra_context)

    @action(
        description='Сгенерировать коды',
        icon='add_circle',
        permissions=('add',),
        variant=ActionVariant.PRIMARY,
        dialog={
            'title': 'Генерация промокодов',
            'description': (
                'Укажите, сколько новых уникальных кодов добавить к текущему '
                'пулу. Задача будет выполнена в фоне через Celery.'
            ),
            'form_class': PromoCodeGenerationForm,
            'form_submit_text': 'Запустить',
        },
    )
    def generate_codes(self, request, form):
        try:
            with transaction.atomic():
                generation = PromoCodeGeneration.objects.create(
                    requested_count=form.cleaned_data['count'],
                    created_by=request.user,
                )
        except IntegrityError:
            messages.warning(
                request,
                'Дождитесь завершения текущей генерации промокодов.',
            )
            return redirect('admin:promo_promocode_changelist')

        try:
            task = generate_promo_codes_task.delay(generation.pk)
        except Exception as error:
            generation.status = PromoCodeGeneration.Status.FAILED
            generation.error = str(error)[:2000]
            generation.finished_at = timezone.now()
            generation.save(update_fields=('status', 'error', 'finished_at'))
            messages.error(
                request,
                'Не удалось отправить задачу в Celery. Проверьте Redis и worker.',
            )
        else:
            generation.celery_task_id = task.id
            generation.save(update_fields=('celery_task_id',))
            messages.success(
                request,
                f'Генерация {generation.requested_count:,} кодов поставлена в очередь.',
            )

        return redirect('admin:promo_promocode_changelist')

    @admin.display(boolean=True, description='Зарегистрирован')
    def is_registered(self, obj):
        return obj.registered_by_id is not None

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PromoCodeAttempt)
class PromoCodeAttemptAdmin(ModelAdmin):
    list_display = ('user', 'normalized_code', 'result', 'reason', 'created_at')
    list_filter = ('result', 'reason', 'created_at')
    search_fields = ('user__email', 'normalized_code', 'ip_address')
    readonly_fields = (
        'user',
        'raw_code',
        'normalized_code',
        'result',
        'reason',
        'ip_address',
        'created_at',
    )
    list_select_related = ('user',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_per_page = 100

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PromoCodeGeneration)
class PromoCodeGenerationAdmin(ModelAdmin):
    list_display = (
        'created_at',
        'status',
        'requested_count',
        'generated_count',
        'progress',
        'created_by',
        'finished_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('celery_task_id', 'created_by__email')
    readonly_fields = (
        'requested_count',
        'generated_count',
        'status',
        'created_by',
        'celery_task_id',
        'error',
        'created_at',
        'started_at',
        'finished_at',
    )
    list_select_related = ('created_by',)
    ordering = ('-created_at',)

    @admin.display(description='Прогресс')
    def progress(self, obj):
        return f'{obj.progress_percent}%'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

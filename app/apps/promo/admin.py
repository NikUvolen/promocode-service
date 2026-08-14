from pathlib import Path

from django.contrib import admin, messages
from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.decorators import action
from unfold.enums import ActionVariant
from unfold.admin import ModelAdmin

from core.audit import log_audit_event
from core.models import AuditLog

from .forms import PromoCodeGenerationForm, PromoCodeImportForm
from .models import (
    PromoCode,
    PromoCodeAttempt,
    PromoCodeGeneration,
    PromoCodeImport,
)
from .tasks import generate_promo_codes_task, import_promo_codes_task


def redirect_from_dialog(request, url_name):
    url = reverse(url_name)
    if request.headers.get('HX-Request') == 'true':
        response = HttpResponse(status=204)
        response['HX-Redirect'] = url
        return response
    return redirect(url)


@admin.register(PromoCode)
class PromoCodeAdmin(ModelAdmin):
    actions_list = ('generate_codes', 'import_codes')
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
            return redirect_from_dialog(
                request,
                'admin:promo_promocodegeneration_changelist',
            )

        try:
            task = generate_promo_codes_task.delay(generation.pk)
        except Exception as error:
            generation.status = PromoCodeGeneration.Status.FAILED
            generation.error = str(error)[:2000]
            generation.finished_at = timezone.now()
            generation.save(update_fields=('status', 'error', 'finished_at'))
            log_audit_event(
                AuditLog.EventType.PROMO_GENERATION_FAILED,
                actor=request.user,
                target=generation,
                metadata={
                    'requested_count': generation.requested_count,
                    'error': str(error)[:500],
                },
            )
            messages.error(
                request,
                'Не удалось отправить задачу в Celery. Проверьте Redis и worker.',
            )
        else:
            generation.celery_task_id = task.id
            generation.save(update_fields=('celery_task_id',))
            log_audit_event(
                AuditLog.EventType.PROMO_GENERATION_QUEUED,
                actor=request.user,
                target=generation,
                metadata={
                    'requested_count': generation.requested_count,
                    'celery_task_id': task.id,
                },
            )
            messages.success(
                request,
                f'Генерация {generation.requested_count:,} кодов поставлена в очередь. '
                'Статус можно отслеживать в журнале генераций.',
            )

        return redirect_from_dialog(request, 'admin:promo_promocodegeneration_changelist')

    @action(
        description='Импортировать XLSX',
        icon='upload_file',
        permissions=('add',),
        variant=ActionVariant.PRIMARY,
        dialog={
            'title': 'Импорт промокодов из XLSX',
            'description': (
                'Коды будут добавлены в фоне. Некорректные и повторяющиеся '
                'строки попадут в отдельный файл результатов.'
            ),
            'form_class': PromoCodeImportForm,
            'form_submit_text': 'Запустить импорт',
        },
    )
    def import_codes(self, request, form):
        uploaded_file = form.cleaned_data['file']
        import_job = PromoCodeImport.objects.create(
            source_file=uploaded_file,
            original_filename=Path(uploaded_file.name).name,
            created_by=request.user,
        )

        try:
            task = import_promo_codes_task.delay(import_job.pk)
        except Exception as error:
            import_job.status = PromoCodeImport.Status.FAILED
            import_job.error = str(error)[:2000]
            import_job.finished_at = timezone.now()
            import_job.save(update_fields=('status', 'error', 'finished_at'))
            log_audit_event(
                AuditLog.EventType.PROMO_IMPORT_FAILED,
                actor=request.user,
                target=import_job,
                metadata={
                    'original_filename': import_job.original_filename,
                    'error': str(error)[:500],
                },
            )
            messages.error(
                request,
                'Не удалось отправить импорт в Celery. Проверьте Redis и worker.',
            )
        else:
            import_job.celery_task_id = task.id
            import_job.save(update_fields=('celery_task_id',))
            log_audit_event(
                AuditLog.EventType.PROMO_IMPORT_QUEUED,
                actor=request.user,
                target=import_job,
                metadata={
                    'original_filename': import_job.original_filename,
                    'celery_task_id': task.id,
                },
            )
            messages.success(
                request,
                'Импорт поставлен в очередь. Результат появится в журнале '
                'импортов.',
            )

        return redirect_from_dialog(request, 'admin:promo_promocodeimport_changelist')

    @admin.display(boolean=True, description='Зарегистрирован')
    def is_registered(self, obj):
        return obj.registered_by_id is not None

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PromoCodeAttempt)
class PromoCodeAttemptAdmin(ModelAdmin):
    list_display = ('user', 'normalized_code', 'result', 'reason', 'created_at')
    list_filter = ('result', 'reason', 'created_at')
    search_fields = ('user__email', 'normalized_code')
    readonly_fields = (
        'user',
        'raw_code',
        'normalized_code',
        'result',
        'reason',
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


@admin.register(PromoCodeImport)
class PromoCodeImportAdmin(ModelAdmin):
    list_display = (
        'created_at',
        'original_filename',
        'status',
        'processed_count',
        'imported_count',
        'skipped_count',
        'created_by',
        'error_download',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('original_filename', 'celery_task_id', 'created_by__email')
    readonly_fields = (
        'original_filename',
        'status',
        'processed_count',
        'imported_count',
        'skipped_count',
        'created_by',
        'celery_task_id',
        'error',
        'source_download',
        'error_download',
        'created_at',
        'started_at',
        'finished_at',
    )
    list_select_related = ('created_by',)
    ordering = ('-created_at',)

    def get_urls(self):
        custom_urls = [
            path(
                '<int:object_id>/download-source/',
                self.admin_site.admin_view(self.download_source),
                name='promo_promocodeimport_download_source',
            ),
            path(
                '<int:object_id>/download-errors/',
                self.admin_site.admin_view(self.download_errors),
                name='promo_promocodeimport_download_errors',
            ),
        ]
        return custom_urls + super().get_urls()

    def download_source(self, request, object_id):
        import_job = get_object_or_404(PromoCodeImport, pk=object_id)
        return self._download_file(
            request,
            import_job,
            import_job.source_file,
            import_job.original_filename,
        )

    def download_errors(self, request, object_id):
        import_job = get_object_or_404(PromoCodeImport, pk=object_id)
        return self._download_file(
            request,
            import_job,
            import_job.error_file,
            f'import-{import_job.pk}-errors.xlsx',
        )

    def _download_file(self, request, import_job, field, filename):
        if not self.has_view_permission(request, import_job) or not field:
            raise Http404
        try:
            return FileResponse(
                field.open('rb'),
                as_attachment=True,
                filename=filename,
            )
        except FileNotFoundError as error:
            raise Http404 from error

    @admin.display(description='Исходный файл')
    def source_download(self, obj):
        if not obj or not obj.source_file:
            return 'Удалён по сроку хранения'
        url = reverse(
            'admin:promo_promocodeimport_download_source',
            args=(obj.pk,),
        )
        return format_html('<a href="{}">Скачать</a>', url)

    @admin.display(description='Файл пропусков')
    def error_download(self, obj):
        if not obj or not obj.error_file:
            return '—'
        url = reverse(
            'admin:promo_promocodeimport_download_errors',
            args=(obj.pk,),
        )
        return format_html('<a href="{}">Скачать</a>', url)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

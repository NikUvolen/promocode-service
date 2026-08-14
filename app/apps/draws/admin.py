from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib import admin, messages
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from unfold.enums import ActionVariant

from core.audit import log_audit_event
from core.models import AuditLog

from .forms import DrawReportForm
from .models import Draw, DrawReport, Winner
from .tasks import generate_draw_report_task, run_manual_draw_task


def redirect_from_dialog(request, url_name):
    url = reverse(url_name)
    if request.headers.get('HX-Request') == 'true':
        response = HttpResponse(status=204)
        response['HX-Redirect'] = url
        return response
    return redirect(url)


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
    actions_list = ('run_manual_draw', 'generate_report')
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
        except Exception as error:
            log_audit_event(
                AuditLog.EventType.DRAW_FAILED,
                actor=request.user,
                metadata={
                    'draw_date': draw_date.isoformat(),
                    'trigger': Draw.Trigger.MANUAL,
                    'cutoff': cutoff.isoformat(),
                    'error': str(error)[:500],
                },
            )
            messages.error(
                request,
                'Не удалось отправить задачу в Celery. Проверьте Redis и worker.',
            )
        else:
            log_audit_event(
                AuditLog.EventType.DRAW_QUEUED,
                actor=request.user,
                metadata={
                    'draw_date': draw_date.isoformat(),
                    'trigger': Draw.Trigger.MANUAL,
                    'cutoff': cutoff.isoformat(),
                    'celery_task_id': task.id,
                },
            )
            messages.success(
                request,
                f'Розыгрыш поставлен в очередь. ID задачи: {task.id}.',
            )
        return redirect('admin:draws_draw_changelist')

    @action(
        description='Выгрузить статистику XLSX',
        icon='download',
        permissions=('view',),
        variant=ActionVariant.PRIMARY,
        dialog={
            'title': 'Сформировать отчёт по акции',
            'description': (
                'Укажите период или оставьте даты пустыми для отчёта за всё '
                'время. Файл будет сформирован в фоне через Celery.'
            ),
            'form_class': DrawReportForm,
            'form_submit_text': 'Сформировать',
        },
    )
    def generate_report(self, request, form):
        report = DrawReport.objects.create(
            date_from=form.cleaned_data.get('date_from'),
            date_to=form.cleaned_data.get('date_to'),
            created_by=request.user,
        )
        try:
            task = generate_draw_report_task.delay(report.pk)
        except Exception as error:
            report.status = DrawReport.Status.FAILED
            report.error = str(error)[:2000]
            report.finished_at = timezone.now()
            report.save(update_fields=('status', 'error', 'finished_at'))
            log_audit_event(
                AuditLog.EventType.DRAW_REPORT_FAILED,
                actor=request.user,
                target=report,
                metadata={'error': str(error)[:500]},
            )
            messages.error(
                request,
                'Не удалось отправить отчёт в Celery. Проверьте Redis и worker.',
            )
        else:
            report.celery_task_id = task.id
            report.save(update_fields=('celery_task_id',))
            log_audit_event(
                AuditLog.EventType.DRAW_REPORT_QUEUED,
                actor=request.user,
                target=report,
                metadata={
                    'date_from': (
                        report.date_from.isoformat()
                        if report.date_from
                        else None
                    ),
                    'date_to': (
                        report.date_to.isoformat()
                        if report.date_to
                        else None
                    ),
                    'celery_task_id': task.id,
                },
            )
            messages.success(
                request,
                'Отчёт поставлен в очередь. После завершения Celery ссылка '
                '«Скачать» появится в созданной строке журнала отчётов.',
            )
        return redirect_from_dialog(
            request,
            'admin:draws_drawreport_changelist',
        )

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


@admin.register(DrawReport)
class DrawReportAdmin(ModelAdmin):
    list_display = (
        'created_at',
        'date_from',
        'date_to',
        'status',
        'created_by',
        'report_download',
        'finished_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('celery_task_id', 'created_by__email')
    readonly_fields = (
        'date_from',
        'date_to',
        'status',
        'created_by',
        'celery_task_id',
        'error',
        'report_download',
        'created_at',
        'started_at',
        'finished_at',
    )
    list_select_related = ('created_by',)
    ordering = ('-created_at',)

    def get_urls(self):
        custom_urls = [
            path(
                '<int:object_id>/download/',
                self.admin_site.admin_view(self.download_report),
                name='draws_drawreport_download',
            ),
        ]
        return custom_urls + super().get_urls()

    def download_report(self, request, object_id):
        report = get_object_or_404(DrawReport, pk=object_id)
        if (
            not self.has_view_permission(request, report)
            or not report.report_file
        ):
            raise Http404
        try:
            return FileResponse(
                report.report_file.open('rb'),
                as_attachment=True,
                filename=f'draw-report-{report.date_from}-{report.date_to}.xlsx',
            )
        except FileNotFoundError as error:
            raise Http404 from error

    @admin.display(description='Отчёт')
    def report_download(self, obj):
        if not obj or not obj.report_file:
            return '—'
        url = reverse('admin:draws_drawreport_download', args=(obj.pk,))
        return format_html('<a href="{}">Скачать</a>', url)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

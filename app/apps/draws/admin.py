from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Draw, Winner


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
    list_display = (
        'draw_date',
        'status',
        'trigger',
        'started_at',
        'completed_at',
    )
    list_filter = ('status', 'trigger', 'draw_date')
    search_fields = ('draw_date',)
    readonly_fields = (
        'draw_date',
        'status',
        'trigger',
        'started_at',
        'completed_at',
        'created_at',
        'updated_at',
    )
    date_hierarchy = 'draw_date'
    inlines = (WinnerInline,)

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

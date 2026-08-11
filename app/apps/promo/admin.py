from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import PromoCode, PromoCodeAttempt


@admin.register(PromoCode)
class PromoCodeAdmin(ModelAdmin):
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

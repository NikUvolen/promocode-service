from django.contrib import admin

from unfold.admin import ModelAdmin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = (
        'created_at',
        'event_type',
        'actor',
        'target_model',
        'target_object_id',
    )
    list_filter = ('event_type', 'created_at')
    search_fields = (
        'actor__email',
        'target_model',
        'target_object_id',
    )
    readonly_fields = (
        'event_type',
        'actor',
        'target_model',
        'target_object_id',
        'metadata',
        'created_at',
    )
    list_select_related = ('actor',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

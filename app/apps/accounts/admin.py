from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin, StackedInline
from unfold.forms import (
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)

from .models import Profile, User


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email',)


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'


class ProfileInline(StackedInline):
    model = Profile
    extra = 0
    max_num = 1
    can_delete = False
    fields = (
        ('last_name', 'first_name'),
        ('middle_name', 'no_middle_name'),
        'phone',
        'personal_data_consent_at',
        'promo_code_email_notifications',
        ('created_at', 'updated_at'),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    change_password_form = AdminPasswordChangeForm
    inlines = (ProfileInline,)

    list_display = (
        'email',
        'is_email_verified',
        'profile_complete',
        'is_active',
        'is_staff',
        'date_joined',
    )
    list_filter = ('is_email_verified', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'profile__phone', 'profile__last_name')
    ordering = ('-date_joined',)
    readonly_fields = ('last_login', 'date_joined')
    list_select_related = ('profile',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (
            'Статусы',
            {'fields': ('is_active', 'is_email_verified', 'is_staff')},
        ),
        (
            'Права доступа',
            {
                'fields': ('is_superuser', 'groups', 'user_permissions'),
                'classes': ('collapse',),
            },
        ),
        ('Системная информация', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'password1',
                    'password2',
                    'is_active',
                    'is_staff',
                ),
            },
        ),
    )
    filter_horizontal = ('groups', 'user_permissions')

    @admin.display(boolean=True, description='Профиль заполнен')
    def profile_complete(self, obj):
        try:
            return obj.profile.is_complete
        except Profile.DoesNotExist:
            return False


@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = (
        'user',
        'last_name',
        'first_name',
        'phone',
        'complete',
        'promo_code_email_notifications',
        'updated_at',
    )
    list_filter = (
        'no_middle_name',
        'promo_code_email_notifications',
        'personal_data_consent_at',
    )
    search_fields = ('user__email', 'last_name', 'first_name', 'phone')
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('user',)

    @admin.display(boolean=True, description='Заполнен')
    def complete(self, obj):
        return obj.is_complete


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass

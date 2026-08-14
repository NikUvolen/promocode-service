from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, Max, Min, Q
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
    readonly_fields = (
        'last_login',
        'date_joined',
        'registered_promo_codes_count',
        'total_attempts_count',
        'successful_attempts_count',
        'failed_attempts_count',
        'blocked_attempts_count',
        'successful_attempts_rate',
        'first_promo_registered_at',
        'last_promo_registered_at',
        'last_attempt_at',
        'winner_summary',
    )
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
        (
            'Статистика участия',
            {
                'fields': (
                    (
                        'registered_promo_codes_count',
                        'total_attempts_count',
                    ),
                    (
                        'successful_attempts_count',
                        'failed_attempts_count',
                        'blocked_attempts_count',
                    ),
                    'successful_attempts_rate',
                    (
                        'first_promo_registered_at',
                        'last_promo_registered_at',
                    ),
                    'last_attempt_at',
                    'winner_summary',
                ),
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

    def _participation_statistics(self, obj):
        cache_attribute = '_admin_participation_statistics'
        if hasattr(obj, cache_attribute):
            return getattr(obj, cache_attribute)

        from promo.models import PromoCodeAttempt

        promo_codes = obj.promo_codes.aggregate(
            promo_codes_total=Count('pk'),
            first_registered_at=Min('registered_at'),
            last_registered_at=Max('registered_at'),
        )
        attempts = obj.promo_code_attempts.aggregate(
            attempts_total=Count('pk'),
            successful=Count(
                'pk',
                filter=Q(result=PromoCodeAttempt.Result.SUCCESS),
            ),
            failed=Count(
                'pk',
                filter=Q(result=PromoCodeAttempt.Result.FAILURE),
            ),
            blocked=Count(
                'pk',
                filter=Q(result=PromoCodeAttempt.Result.BLOCKED),
            ),
            last_attempt_at=Max('created_at'),
        )
        winner = obj.wins.select_related('draw', 'promo_code').first()
        statistics = {
            **promo_codes,
            **attempts,
            'winner': winner,
        }
        setattr(obj, cache_attribute, statistics)
        return statistics

    @admin.display(description='Зарегистрировано промокодов')
    def registered_promo_codes_count(self, obj):
        return self._participation_statistics(obj)['promo_codes_total']

    @admin.display(description='Всего попыток ввода')
    def total_attempts_count(self, obj):
        return self._participation_statistics(obj)['attempts_total']

    @admin.display(description='Успешных попыток')
    def successful_attempts_count(self, obj):
        return self._participation_statistics(obj)['successful']

    @admin.display(description='Неудачных попыток')
    def failed_attempts_count(self, obj):
        return self._participation_statistics(obj)['failed']

    @admin.display(description='Заблокированных попыток')
    def blocked_attempts_count(self, obj):
        return self._participation_statistics(obj)['blocked']

    @admin.display(description='Доля успешных попыток')
    def successful_attempts_rate(self, obj):
        statistics = self._participation_statistics(obj)
        if not statistics['attempts_total']:
            return '0%'
        return (
            f"{statistics['successful'] / statistics['attempts_total']:.1%}"
        )

    @admin.display(description='Первый промокод зарегистрирован')
    def first_promo_registered_at(self, obj):
        return self._participation_statistics(obj)['first_registered_at'] or '—'

    @admin.display(description='Последний промокод зарегистрирован')
    def last_promo_registered_at(self, obj):
        return self._participation_statistics(obj)['last_registered_at'] or '—'

    @admin.display(description='Последняя попытка ввода')
    def last_attempt_at(self, obj):
        return self._participation_statistics(obj)['last_attempt_at'] or '—'

    @admin.display(description='Результат участия')
    def winner_summary(self, obj):
        winner = self._participation_statistics(obj)['winner']
        if winner is None:
            return 'Побед нет'
        return (
            f'{winner.get_prize_display()} — '
            f'{winner.draw.draw_date:%d.%m.%Y}, код {winner.promo_code.code}'
        )


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

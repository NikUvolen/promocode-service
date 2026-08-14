from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'
    verbose_name = 'Пользователи'

    def ready(self):
        from accounts.api import schema  # noqa: F401

from django.apps import AppConfig


class DrawsConfig(AppConfig):
    name = 'draws'
    verbose_name = 'Розыгрыши'

    def ready(self):
        import draws.signals  # noqa: F401

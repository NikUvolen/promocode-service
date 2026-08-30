from datetime import date

from django.core.management.base import BaseCommand, CommandError

from draws.tasks import run_daily_draw_task


class Command(BaseCommand):
    help = 'Проводит все пропущенные ежедневные розыгрыши до указанной даты.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--through',
            type=date.fromisoformat,
            help='Включительно, в формате YYYY-MM-DD. По умолчанию — вчера.',
        )

    def handle(self, *args, **options):
        try:
            result = run_daily_draw_task(options['through'])
        except ValueError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(
            self.style.SUCCESS(
                f"Проведено розыгрышей: {result['draw_count']}."
            )
        )
        for draw in result['draws']:
            self.stdout.write(
                f"{draw['draw_date']}: победителей — {draw['winner_count']}."
            )

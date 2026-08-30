import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from openpyxl import Workbook

from promo.models import PromoCodeGeneration, PromoCodeImport
from promo.services.generation import ALPHABET, CODE_SPACE_SIZE
from promo.tasks import generate_promo_codes_task, import_promo_codes_task


MAX_XLSX_ROWS = 1_048_576
DEFAULT_GENERATION_COUNT = 1_500_000


def encode_code(number):
    characters = ['0'] * 8
    for index in range(7, -1, -1):
        number, remainder = divmod(number, len(ALPHABET))
        characters[index] = ALPHABET[remainder]
    return ''.join(characters)


def load_test_code(index):
    return encode_code((index * 1_103_515_245 + 12_345) % CODE_SPACE_SIZE)


def build_import_workbook(*, path, target_bytes, max_bytes):
    """Build a valid XLSX close to the configured upload limit."""
    rows = 10_000
    final_size = 0

    for _ in range(6):
        workbook = Workbook(write_only=True)
        worksheet = workbook.create_sheet('Промокоды')
        for index in range(rows):
            padding = hashlib.sha256(str(index).encode()).hexdigest()
            worksheet.append((load_test_code(index), padding))
        workbook.save(path)
        workbook.close()

        final_size = path.stat().st_size
        if final_size > max_bytes:
            rows = max(1, int(rows * target_bytes / final_size * 0.95))
            continue
        if final_size >= target_bytes * 0.98 or rows == MAX_XLSX_ROWS:
            return rows, final_size

        rows = min(
            MAX_XLSX_ROWS,
            max(rows + 1, int(rows * target_bytes / final_size)),
        )

    if final_size > max_bytes:
        raise CommandError('Could not build an XLSX within the upload limit.')
    return rows, final_size


class Command(BaseCommand):
    help = (
        'Runs generation and XLSX-import load scenarios in an isolated '
        'database. Requires LOAD_TEST_ALLOWED=True and --confirm.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--scenario',
            choices=('generation', 'import', 'all'),
            default='all',
        )
        parser.add_argument(
            '--generation-count',
            type=int,
            default=DEFAULT_GENERATION_COUNT,
        )
        parser.add_argument(
            '--import-target-bytes',
            type=int,
            default=settings.XLSX_MAX_UPLOAD_SIZE,
        )
        parser.add_argument('--confirm', action='store_true')

    def handle(self, *args, **options):
        if not settings.LOAD_TEST_ALLOWED:
            raise CommandError('Set LOAD_TEST_ALLOWED=True in a load environment.')
        if not options['confirm']:
            raise CommandError('Pass --confirm to run a load scenario.')

        results = []
        scenario = options['scenario']
        if scenario in ('generation', 'all'):
            results.append(self.run_generation(options['generation_count']))
        if scenario in ('import', 'all'):
            results.append(self.run_import(options['import_target_bytes']))

        self.stdout.write(json.dumps(results, ensure_ascii=False, indent=2))

    def run_generation(self, requested_count):
        if not 1 <= requested_count <= CODE_SPACE_SIZE:
            raise CommandError('generation-count is outside the code space.')

        generation = PromoCodeGeneration.objects.create(
            requested_count=requested_count,
        )
        started_at = perf_counter()
        generate_promo_codes_task(generation.pk)
        duration_seconds = perf_counter() - started_at
        generation.refresh_from_db()

        if generation.status != PromoCodeGeneration.Status.COMPLETED:
            raise CommandError('Promo-code generation did not complete.')

        return {
            'scenario': 'generation',
            'requested_count': requested_count,
            'generated_count': generation.generated_count,
            'duration_seconds': round(duration_seconds, 3),
            'codes_per_second': round(
                generation.generated_count / duration_seconds,
                2,
            ),
        }

    def run_import(self, target_bytes):
        if not 1 <= target_bytes <= settings.XLSX_MAX_UPLOAD_SIZE:
            raise CommandError('import-target-bytes exceeds XLSX_MAX_UPLOAD_SIZE.')

        with TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / 'load-import.xlsx'
            row_count, file_size = build_import_workbook(
                path=source_path,
                target_bytes=target_bytes,
                max_bytes=settings.XLSX_MAX_UPLOAD_SIZE,
            )
            import_job = PromoCodeImport.objects.create(
                original_filename=source_path.name,
            )
            with source_path.open('rb') as source_file:
                import_job.source_file.save(
                    source_path.name,
                    File(source_file),
                    save=True,
                )

            started_at = perf_counter()
            import_promo_codes_task(import_job.pk)
            duration_seconds = perf_counter() - started_at

        import_job.refresh_from_db()
        if import_job.status != PromoCodeImport.Status.COMPLETED:
            raise CommandError('Promo-code import did not complete.')

        return {
            'scenario': 'import',
            'xlsx_rows': row_count,
            'xlsx_size_bytes': file_size,
            'processed_count': import_job.processed_count,
            'imported_count': import_job.imported_count,
            'skipped_count': import_job.skipped_count,
            'duration_seconds': round(duration_seconds, 3),
            'rows_per_second': round(
                import_job.processed_count / duration_seconds,
                2,
            ),
        }

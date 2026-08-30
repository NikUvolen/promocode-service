from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings
from openpyxl import load_workbook

from promo.management.commands.run_load_scenarios import build_import_workbook


class LoadScenarioCommandTests(SimpleTestCase):
    def test_refuses_to_run_without_a_dedicated_load_environment(self):
        with self.assertRaisesMessage(
            CommandError,
            'Set LOAD_TEST_ALLOWED=True in a load environment.',
        ):
            call_command('run_load_scenarios', '--confirm')

    @override_settings(XLSX_MAX_UPLOAD_SIZE=60_000)
    def test_builds_a_valid_workbook_under_the_upload_limit(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / 'load-import.xlsx'
            row_count, size = build_import_workbook(
                path=path,
                target_bytes=50_000,
                max_bytes=60_000,
            )

            self.assertGreater(row_count, 0)
            self.assertLessEqual(size, 60_000)
            workbook = load_workbook(path, read_only=True, data_only=True)
            self.assertEqual(workbook.active['A1'].value, '000009IX')
            workbook.close()

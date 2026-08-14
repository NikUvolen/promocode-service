from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class ApiDocumentationTests(TestCase):
    def test_healthcheck(self):
        response = self.client.get(reverse('healthcheck'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_openapi_schema_contains_auth_endpoints(self):
        response = self.client.get(f"{reverse('schema')}?format=json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        expected_paths = (
            '/api/v1/auth/register/',
            '/api/v1/auth/verify-email/',
            '/api/v1/auth/resend-verification/',
            '/api/v1/auth/login/',
            '/api/v1/auth/refresh/',
            '/api/v1/auth/logout/',
            '/api/v1/auth/password-reset/',
            '/api/v1/auth/password-reset-confirm/',
            '/api/v1/auth/change-password/',
        )
        for path in expected_paths:
            with self.subTest(path=path):
                self.assertIn(path, schema['paths'])

    def test_swagger_ui_renders(self):
        response = self.client.get(reverse('swagger-ui'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="swagger-ui"')


class CeleryQueueRoutingTests(SimpleTestCase):
    def test_routes_tasks_by_workload(self):
        expected_routes = {
            'draws.tasks.run_daily_draw_task': 'critical',
            'draws.tasks.run_manual_draw_task': 'critical',
            'accounts.tasks.send_verification_email_task': 'notifications',
            'accounts.tasks.send_password_reset_email_task': 'notifications',
            'promo.tasks.send_registration_email_task': 'notifications',
            'draws.tasks.send_winner_email_task': 'notifications',
            'promo.tasks.generate_promo_codes_task': 'bulk',
            'promo.tasks.import_promo_codes_task': 'bulk',
            'draws.tasks.generate_draw_report_task': 'bulk',
            'promo.tasks.cleanup_expired_import_files_task': 'bulk',
            'draws.tasks.cleanup_expired_report_files_task': 'bulk',
        }

        self.assertEqual(settings.CELERY_TASK_DEFAULT_QUEUE, 'bulk')
        self.assertEqual(
            {
                task_name: route['queue']
                for task_name, route in settings.CELERY_TASK_ROUTES.items()
            },
            expected_routes,
        )

from datetime import timedelta

from django.conf import settings
from django.test import override_settings, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from config.celery import app as celery_app
from core.models import AuditLog
from core.tasks import cleanup_expired_audit_logs_task


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
            'draws.tasks.retry_unnotified_winner_emails_task': 'notifications',
            'promo.tasks.generate_promo_codes_task': 'bulk',
            'promo.tasks.import_promo_codes_task': 'bulk',
            'draws.tasks.generate_draw_report_task': 'bulk',
            'promo.tasks.cleanup_expired_import_files_task': 'bulk',
            'draws.tasks.cleanup_expired_report_files_task': 'bulk',
            'core.tasks.cleanup_expired_audit_logs_task': 'bulk',
            'core.tasks.fail_stale_background_jobs_task': 'bulk',
        }

        self.assertEqual(settings.CELERY_TASK_DEFAULT_QUEUE, 'bulk')
        self.assertEqual(settings.CELERY_TASK_DEFAULT_EXCHANGE, 'bulk')
        self.assertEqual(settings.CELERY_TASK_DEFAULT_ROUTING_KEY, 'bulk')
        self.assertFalse(settings.CELERY_TASK_CREATE_MISSING_QUEUES)
        self.assertEqual(
            {queue.name for queue in settings.CELERY_TASK_QUEUES},
            {'critical', 'notifications', 'bulk'},
        )
        self.assertEqual(
            {
                queue.name: (queue.exchange.name, queue.routing_key)
                for queue in settings.CELERY_TASK_QUEUES
            },
            {
                'critical': ('critical', 'critical'),
                'notifications': ('notifications', 'notifications'),
                'bulk': ('bulk', 'bulk'),
            },
        )
        self.assertEqual(
            {
                task_name: route['queue']
                for task_name, route in settings.CELERY_TASK_ROUTES.items()
            },
            expected_routes,
        )
        celery_app.autodiscover_tasks(force=True)
        registered_project_tasks = {
            task_name
            for task_name in celery_app.tasks
            if task_name.startswith(('accounts.', 'core.', 'draws.', 'promo.'))
        }
        self.assertEqual(registered_project_tasks, set(expected_routes))
        for task_name, expected_queue in expected_routes.items():
            with self.subTest(task=task_name):
                route = celery_app.amqp.router.route({}, task_name)
                self.assertEqual(route['queue'].name, expected_queue)

    def test_redis_visibility_timeout_covers_long_running_jobs(self):
        visibility_timeout = settings.CELERY_BROKER_TRANSPORT_OPTIONS[
            'visibility_timeout'
        ]

        self.assertGreater(
            visibility_timeout,
            settings.BACKGROUND_JOB_RUNNING_TIMEOUT,
        )

    def test_non_repeatable_tasks_are_acknowledged_after_execution(self):
        celery_app.autodiscover_tasks(force=True)
        reliable_tasks = (
            'accounts.tasks.send_verification_email_task',
            'accounts.tasks.send_password_reset_email_task',
            'promo.tasks.send_registration_email_task',
            'draws.tasks.send_winner_email_task',
            'draws.tasks.run_daily_draw_task',
            'draws.tasks.run_manual_draw_task',
            'promo.tasks.generate_promo_codes_task',
            'promo.tasks.import_promo_codes_task',
            'draws.tasks.generate_draw_report_task',
        )

        for task_name in reliable_tasks:
            with self.subTest(task=task_name):
                task = celery_app.tasks[task_name]
                self.assertTrue(task.acks_late)
                self.assertTrue(task.reject_on_worker_lost)

    def test_every_beat_task_has_an_explicit_route_and_expiration(self):
        routes = settings.CELERY_TASK_ROUTES

        for schedule_name, entry in settings.CELERY_BEAT_SCHEDULE.items():
            with self.subTest(schedule=schedule_name):
                self.assertIn(entry['task'], routes)
                self.assertGreater(entry['options']['expires'], 0)

    def test_beat_registers_audit_cleanup_task(self):
        entry = settings.CELERY_BEAT_SCHEDULE['cleanup-expired-audit-logs']

        self.assertEqual(
            entry['task'],
            'core.tasks.cleanup_expired_audit_logs_task',
        )
        self.assertEqual(entry['options']['expires'], 3600)


class LoggingSettingsTests(SimpleTestCase):
    def test_logging_writes_application_logs_to_console(self):
        self.assertEqual(
            settings.LOGGING['handlers']['console']['class'],
            'logging.StreamHandler',
        )
        self.assertEqual(
            settings.LOGGING['loggers']['promo']['handlers'],
            ['console'],
        )
        self.assertEqual(
            settings.LOGGING['loggers']['draws']['level'],
            settings.APP_LOG_LEVEL,
        )


class AuditLogCleanupTests(TestCase):
    @override_settings(AUDIT_LOG_RETENTION_DAYS=180)
    def test_cleanup_deletes_expired_audit_logs_and_keeps_recent_logs(self):
        user = User.objects.create_user(
            email='auditor@example.com',
            password='test-password',
        )
        old_log = AuditLog.objects.create(
            event_type=AuditLog.EventType.PROMO_IMPORT_COMPLETED,
            actor=user,
            metadata={'imported_count': 10},
        )
        recent_log = AuditLog.objects.create(
            event_type=AuditLog.EventType.DRAW_REPORT_COMPLETED,
            actor=user,
            metadata={'filename': 'report.xlsx'},
        )
        AuditLog.objects.filter(pk=old_log.pk).update(
            created_at=timezone.now() - timedelta(days=181),
        )

        deleted_count = cleanup_expired_audit_logs_task()

        self.assertEqual(deleted_count, 1)
        self.assertFalse(AuditLog.objects.filter(pk=old_log.pk).exists())
        self.assertTrue(AuditLog.objects.filter(pk=recent_log.pk).exists())
        cleanup_log = AuditLog.objects.get(
            event_type=AuditLog.EventType.AUDIT_CLEANUP_COMPLETED,
        )
        self.assertEqual(cleanup_log.metadata['deleted_count'], 1)

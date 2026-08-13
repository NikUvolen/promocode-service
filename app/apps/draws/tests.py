from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.db import connections, IntegrityError, transaction
from django.core import mail
from django.test import TestCase, TransactionTestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile, User
from draws.models import Draw, Winner
from draws.services.draw import InvalidDrawPeriod, run_draw
from draws.services.notifications import send_winner_email
from draws.tasks import run_daily_draw_task
from promo.models import PromoCode


class DrawsAdminTests(TestCase):
    def setUp(self):
        admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='test-password',
        )
        self.client.force_login(admin_user)

    def test_draw_admin_pages_render(self):
        urls = (
            reverse('admin:draws_draw_changelist'),
            reverse('admin:draws_winner_changelist'),
        )

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    @patch('draws.admin.timezone.now')
    @patch('draws.admin.run_manual_draw_task.delay')
    def test_starts_manual_draw_from_admin(self, delay, now):
        cutoff = datetime(
            2026, 8, 13, 9, 30, tzinfo=ZoneInfo('Europe/Moscow')
        )
        now.return_value = cutoff
        delay.return_value = SimpleNamespace(id='manual-task-id')

        response = self.client.post(
            reverse('admin:draws_draw_run_manual_draw'),
            {'_form_submitted': True},
        )

        self.assertRedirects(
            response,
            reverse('admin:draws_draw_changelist'),
        )
        delay.assert_called_once_with(
            '2026-08-13',
            cutoff.isoformat(),
        )


class DrawServiceTests(TransactionTestCase):
    draw_date = datetime(2026, 8, 12).date()
    moscow = ZoneInfo('Europe/Moscow')

    def setUp(self):
        self.notification_patcher = patch(
            'draws.services.draw.schedule_winner_emails'
        )
        self.schedule_winner_emails = self.notification_patcher.start()
        self.addCleanup(self.notification_patcher.stop)

    def create_participant(self, index, registered_at=None):
        user = User.objects.create_user(
            email=f'user{index}@example.com',
            password='StrongPassword_123!',
            is_email_verified=True,
        )
        Profile.objects.create(user=user)
        promo_code = PromoCode.objects.create(
            code=f'CD{index:06d}',
            registered_by=user,
            registered_at=(
                registered_at
                or datetime(2026, 8, 12, 12, 0, tzinfo=self.moscow)
            ),
        )
        return user, promo_code

    @patch('draws.services.draw.secrets.randbelow', return_value=0)
    def test_selects_two_winners_from_draw_date(self, random_offset):
        participants = [self.create_participant(index) for index in range(3)]

        draw = run_draw(
            draw_date=self.draw_date,
            trigger=Draw.Trigger.AUTOMATIC,
        )

        draw.refresh_from_db()
        winners = list(draw.winners.order_by('prize'))
        self.assertEqual(draw.status, Draw.Status.COMPLETED)
        self.assertEqual(len(winners), 2)
        self.assertEqual(
            {winner.prize for winner in winners},
            {Winner.Prize.OZON_3000, Winner.Prize.AIRPODS},
        )
        self.assertEqual(len({winner.user_id for winner in winners}), 2)
        self.assertTrue(
            {winner.user_id for winner in winners}.issubset(
                {user.pk for user, _ in participants}
            )
        )
        self.assertEqual(random_offset.call_count, 2)

    @patch('draws.services.draw.secrets.randbelow', return_value=0)
    def test_excludes_past_winner_and_same_user_codes(self, random_offset):
        past_winner, past_code = self.create_participant(
            1,
            datetime(2026, 8, 11, 12, 0, tzinfo=self.moscow),
        )
        past_draw = Draw.objects.create(
            draw_date=self.draw_date - timedelta(days=1),
            status=Draw.Status.COMPLETED,
            completed_at=timezone.now(),
        )
        Winner.objects.create(
            draw=past_draw,
            user=past_winner,
            promo_code=past_code,
            prize=Winner.Prize.OZON_3000,
        )
        PromoCode.objects.create(
            code='PAST0001',
            registered_by=past_winner,
            registered_at=datetime(
                2026, 8, 12, 10, 0, tzinfo=self.moscow
            ),
        )
        first_user, _ = self.create_participant(2)
        PromoCode.objects.create(
            code='SAME0002',
            registered_by=first_user,
            registered_at=datetime(
                2026, 8, 12, 14, 0, tzinfo=self.moscow
            ),
        )
        second_user, _ = self.create_participant(3)

        draw = run_draw(
            draw_date=self.draw_date,
            trigger=Draw.Trigger.AUTOMATIC,
        )

        winner_user_ids = set(
            draw.winners.values_list('user_id', flat=True)
        )
        self.assertEqual(winner_user_ids, {first_user.pk, second_user.pk})
        self.assertNotIn(past_winner.pk, winner_user_ids)

    def test_manual_cutoff_excludes_later_registration(self):
        cutoff = datetime(2026, 8, 12, 15, 0, tzinfo=self.moscow)
        eligible_user, _ = self.create_participant(
            1,
            cutoff - timedelta(minutes=1),
        )
        late_user, _ = self.create_participant(
            2,
            cutoff + timedelta(minutes=1),
        )

        draw = run_draw(
            draw_date=self.draw_date,
            trigger=Draw.Trigger.MANUAL,
            cutoff=cutoff,
        )

        self.assertEqual(draw.winners.count(), 1)
        self.assertEqual(draw.winners.get().user, eligible_user)
        self.assertNotEqual(draw.winners.get().user, late_user)
        self.assertEqual(
            draw.period_started_at,
            datetime(2026, 8, 12, 0, 0, tzinfo=self.moscow),
        )
        self.assertEqual(draw.period_ended_at, cutoff)

    @patch('draws.services.draw.secrets.randbelow', return_value=0)
    def test_next_draw_uses_codes_registered_after_manual_draw(
        self,
        random_offset,
    ):
        manual_cutoff = datetime(
            2026, 8, 12, 12, 0, tzinfo=self.moscow
        )
        self.create_participant(1, manual_cutoff - timedelta(minutes=1))
        manual_draw = run_draw(
            draw_date=self.draw_date,
            trigger=Draw.Trigger.MANUAL,
            cutoff=manual_cutoff,
        )
        late_user, late_code = self.create_participant(
            2,
            manual_cutoff + timedelta(minutes=1),
        )

        next_draw = run_draw(
            draw_date=self.draw_date + timedelta(days=1),
            trigger=Draw.Trigger.AUTOMATIC,
        )

        self.assertEqual(manual_draw.period_ended_at, manual_cutoff)
        self.assertEqual(next_draw.period_started_at, manual_cutoff)
        self.assertEqual(next_draw.winners.count(), 1)
        winner = next_draw.winners.get()
        self.assertEqual(winner.user, late_user)
        self.assertEqual(winner.promo_code, late_code)

    def test_repeat_run_returns_existing_result(self):
        self.create_participant(1)
        self.create_participant(2)
        cutoff = datetime(2026, 8, 12, 23, 0, tzinfo=self.moscow)
        first_draw = run_draw(
            draw_date=self.draw_date,
            trigger=Draw.Trigger.MANUAL,
            cutoff=cutoff,
        )
        winner_ids = list(
            first_draw.winners.order_by('pk').values_list('pk', flat=True)
        )

        repeated_draw = run_draw(
            draw_date=self.draw_date,
            trigger=Draw.Trigger.AUTOMATIC,
        )

        self.assertEqual(repeated_draw.pk, first_draw.pk)
        self.assertEqual(
            list(
                repeated_draw.winners.order_by('pk').values_list(
                    'pk', flat=True
                )
            ),
            winner_ids,
        )
        repeated_draw.refresh_from_db()
        self.assertEqual(repeated_draw.trigger, Draw.Trigger.MANUAL)
        self.assertEqual(self.schedule_winner_emails.call_count, 2)

    def test_rejects_naive_or_invalid_cutoff(self):
        with self.assertRaises(InvalidDrawPeriod):
            run_draw(
                draw_date=self.draw_date,
                trigger=Draw.Trigger.MANUAL,
                cutoff=datetime(2026, 8, 12, 12, 0),
            )

        with self.assertRaises(InvalidDrawPeriod):
            run_draw(
                draw_date=self.draw_date,
                trigger=Draw.Trigger.MANUAL,
                cutoff=datetime(
                    2026, 8, 12, 0, 0, tzinfo=self.moscow
                ),
            )

    def test_concurrent_runs_create_one_draw_and_one_set_of_winners(self):
        self.create_participant(1)
        self.create_participant(2)
        self.create_participant(3)
        barrier = Barrier(2)

        def start_draw():
            connections.close_all()
            try:
                barrier.wait(timeout=5)
                return run_draw(
                    draw_date=self.draw_date,
                    trigger=Draw.Trigger.AUTOMATIC,
                ).pk
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            draw_ids = [
                future.result(timeout=10)
                for future in (
                    executor.submit(start_draw),
                    executor.submit(start_draw),
                )
            ]

        self.assertEqual(len(set(draw_ids)), 1)
        self.assertEqual(Draw.objects.count(), 1)
        self.assertEqual(Winner.objects.count(), 2)


class DrawConstraintTests(TransactionTestCase):
    def test_rejects_invalid_draw_status_and_trigger(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Draw.objects.create(
                draw_date=datetime(2026, 8, 12).date(),
                status='SUCCES',
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Draw.objects.create(
                draw_date=datetime(2026, 8, 12).date(),
                trigger='CELRY',
            )

    def test_rejects_invalid_prize(self):
        user = User.objects.create_user(
            email='winner@example.com',
            password='StrongPassword_123!',
        )
        promo_code = PromoCode.objects.create(
            code='WINN0001',
            registered_by=user,
            registered_at=timezone.now(),
        )
        draw = Draw.objects.create(
            draw_date=timezone.localdate(),
            status=Draw.Status.COMPLETED,
            completed_at=timezone.now(),
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Winner.objects.create(
                draw=draw,
                user=user,
                promo_code=promo_code,
                prize='Ozon3000',
            )


class DailyDrawTaskTests(TestCase):
    @patch('draws.tasks.run_draw')
    @patch('draws.tasks.timezone.now')
    def test_draws_previous_moscow_date(self, now, draw_service):
        now.return_value = datetime(
            2026,
            8,
            11,
            21,
            0,
            tzinfo=ZoneInfo('UTC'),
        )
        draw_service.return_value = SimpleNamespace(
            pk=42,
            draw_date=datetime(2026, 8, 11).date(),
            winners=SimpleNamespace(count=lambda: 2),
        )

        result = run_daily_draw_task()

        draw_service.assert_called_once_with(
            draw_date=datetime(2026, 8, 11).date(),
            trigger=Draw.Trigger.AUTOMATIC,
        )
        self.assertEqual(
            result,
            {
                'draw_id': 42,
                'draw_date': '2026-08-11',
                'winner_count': 2,
                'already_completed': False,
            },
        )

    @override_settings(TIME_ZONE='Europe/Moscow')
    def test_beat_registers_daily_draw_task(self):
        from django.conf import settings

        entry = settings.CELERY_BEAT_SCHEDULE[
            'run-daily-draw-at-moscow-midnight'
        ]

        self.assertEqual(entry['task'], 'draws.tasks.run_daily_draw_task')
        self.assertEqual(entry['options']['expires'], 3600)


class WinnerNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='winner@example.com',
            password='StrongPassword_123!',
        )
        Profile.objects.create(
            user=self.user,
            promo_code_email_notifications=False,
        )
        self.promo_code = PromoCode.objects.create(
            code='PRIZE001',
            registered_by=self.user,
            registered_at=timezone.now(),
        )
        self.draw = Draw.objects.create(
            draw_date=timezone.localdate(),
            status=Draw.Status.COMPLETED,
            completed_at=timezone.now(),
        )
        self.winner = Winner.objects.create(
            draw=self.draw,
            user=self.user,
            promo_code=self.promo_code,
            prize=Winner.Prize.AIRPODS,
        )

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_sends_mandatory_winner_email_and_marks_notification(self):
        sent = send_winner_email(self.winner.pk)

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn('AirPods', mail.outbox[0].body)
        self.assertIn(self.promo_code.code, mail.outbox[0].body)
        self.winner.refresh_from_db()
        self.assertIsNotNone(self.winner.notified_at)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_does_not_send_winner_email_twice(self):
        self.assertTrue(send_winner_email(self.winner.pk))
        self.assertFalse(send_winner_email(self.winner.pk))

        self.assertEqual(len(mail.outbox), 1)

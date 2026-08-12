from unittest.mock import patch

from django.core import mail
from django.test import override_settings, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile, User
from accounts.services.authentication import create_token_pair
from promo.models import PromoCode, PromoCodeAttempt
from promo.services.notifications import send_registration_email


class PromoAdminTests(TestCase):
    def setUp(self):
        admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='test-password',
        )
        self.client.force_login(admin_user)

    def test_promo_admin_pages_render(self):
        urls = (
            reverse('admin:promo_promocode_changelist'),
            reverse('admin:promo_promocodeattempt_changelist'),
        )

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)


class PromoCodeApiTests(TestCase):
    list_url = reverse('promo-code-list')
    register_url = reverse('promo-code-register')

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='StrongPassword_123!',
            is_email_verified=True,
        )
        self.profile = Profile.objects.create(
            user=self.user,
            first_name='Михаил',
            last_name='Иванов',
            no_middle_name=True,
            phone='+7 (999) 123-45-67',
            personal_data_consent_at=timezone.now(),
        )
        self.tokens = create_token_pair(self.user)

    def register(self, code):
        return self.client.post(
            self.register_url,
            {'code': code},
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {self.tokens['access']}",
            REMOTE_ADDR='127.0.0.2',
        )

    def test_requires_authentication(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 401)

    @patch('promo.services.notifications.schedule_registration_email')
    def test_registers_existing_code(self, schedule_email):
        promo_code = PromoCode.objects.create(code='AB12CD34')

        with self.captureOnCommitCallbacks(execute=True):
            response = self.register('ab12cd34')

        self.assertEqual(response.status_code, 201)
        promo_code.refresh_from_db()
        self.assertEqual(promo_code.registered_by, self.user)
        self.assertIsNotNone(promo_code.registered_at)
        attempt = PromoCodeAttempt.objects.get()
        self.assertEqual(attempt.result, PromoCodeAttempt.Result.SUCCESS)
        self.assertEqual(attempt.ip_address, '127.0.0.2')
        schedule_email.assert_called_once_with(promo_code.pk)

    def test_requires_completed_profile(self):
        self.profile.first_name = ''
        self.profile.save()
        PromoCode.objects.create(code='AB12CD34')

        response = self.register('AB12CD34')

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['reason'], 'profile_incomplete')
        self.assertEqual(
            PromoCodeAttempt.objects.get().result,
            PromoCodeAttempt.Result.BLOCKED,
        )

    def test_rejects_invalid_format_and_missing_code(self):
        invalid_response = self.register('ABC')
        missing_response = self.register('ZZ99ZZ99')

        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(
            invalid_response.json()['reason'],
            PromoCodeAttempt.Reason.INVALID_FORMAT,
        )
        self.assertEqual(missing_response.status_code, 400)
        self.assertEqual(
            missing_response.json()['reason'],
            PromoCodeAttempt.Reason.NOT_FOUND,
        )

    def test_counts_empty_and_long_codes_as_failed_attempts(self):
        empty_response = self.register('')
        long_response = self.register('A' * 100)

        self.assertEqual(empty_response.status_code, 400)
        self.assertEqual(long_response.status_code, 400)
        self.assertEqual(
            PromoCodeAttempt.objects.filter(
                result=PromoCodeAttempt.Result.FAILURE,
                reason=PromoCodeAttempt.Reason.INVALID_FORMAT,
            ).count(),
            2,
        )
        self.assertEqual(
            PromoCodeAttempt.objects.order_by('-created_at')
            .first()
            .raw_code,
            'A' * 64,
        )

    def test_rejects_already_registered_code(self):
        other_user = User.objects.create_user(
            email='other@example.com',
            password='StrongPassword_123!',
        )
        PromoCode.objects.create(
            code='AB12CD34',
            registered_by=other_user,
            registered_at=timezone.now(),
        )

        response = self.register('AB12CD34')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['reason'], 'already_registered')

    def test_blocks_for_five_minutes_after_three_recent_failures(self):
        PromoCode.objects.create(code='AB12CD34')
        for code in ('AA11AA11', 'BB22BB22', 'CC33CC33'):
            self.assertEqual(self.register(code).status_code, 400)

        blocked_response = self.register('AB12CD34')
        repeated_response = self.register('AB12CD34')

        self.assertEqual(blocked_response.status_code, 429)
        self.assertEqual(blocked_response.json()['retry_after'], 300)
        self.assertEqual(repeated_response.status_code, 429)
        self.assertEqual(
            PromoCodeAttempt.objects.filter(
                result=PromoCodeAttempt.Result.BLOCKED,
                reason=PromoCodeAttempt.Reason.RATE_LIMIT,
            ).count(),
            1,
        )
        self.assertFalse(
            PromoCode.objects.get(code='AB12CD34').registered_by_id
        )

    def test_lists_only_current_user_codes(self):
        other_user = User.objects.create_user(
            email='other@example.com',
            password='StrongPassword_123!',
        )
        PromoCode.objects.create(
            code='AB12CD34',
            registered_by=self.user,
            registered_at=timezone.now(),
        )
        PromoCode.objects.create(
            code='EF56GH78',
            registered_by=other_user,
            registered_at=timezone.now(),
        )

        response = self.client.get(
            self.list_url,
            HTTP_AUTHORIZATION=f"Bearer {self.tokens['access']}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['results'][0]['code'], 'AB12CD34')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_registration_email_respects_profile_setting(self):
        promo_code = PromoCode.objects.create(
            code='AB12CD34',
            registered_by=self.user,
            registered_at=timezone.now(),
        )

        send_registration_email(promo_code.pk)
        self.assertEqual(len(mail.outbox), 1)

        self.profile.promo_code_email_notifications = False
        self.profile.save()
        send_registration_email(promo_code.pk)
        self.assertEqual(len(mail.outbox), 1)

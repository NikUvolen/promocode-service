from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

from .models import Profile, User
from .services.email_verification import (
    create_email_verification_token,
    send_verification_email,
)


class AccountsAdminTests(TestCase):
    def setUp(self):
        admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='test-password',
        )
        self.client.force_login(admin_user)

    def test_user_admin_pages_render(self):
        urls = (
            reverse('admin:accounts_user_changelist'),
            reverse('admin:accounts_user_add'),
            reverse('admin:accounts_profile_changelist'),
        )

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)


class RegistrationApiTests(TestCase):
    register_url = reverse('auth-register')
    verify_email_url = reverse('auth-verify-email')
    resend_url = reverse('auth-resend-verification')

    @patch('accounts.services.registration.schedule_verification_email')
    def test_registers_user_and_profile(self, schedule_email):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                self.register_url,
                {
                    'email': 'USER@Example.com',
                    'password': 'StrongPassword_123!',
                    'personal_data_consent': True,
                },
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email='user@example.com')
        self.assertTrue(user.check_password('StrongPassword_123!'))
        self.assertFalse(user.is_email_verified)
        self.assertIsNotNone(user.profile.personal_data_consent_at)
        schedule_email.assert_called_once_with(user.pk)

    def test_requires_personal_data_consent(self):
        response = self.client.post(
            self.register_url,
            {
                'email': 'user@example.com',
                'password': 'StrongPassword_123!',
                'personal_data_consent': False,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_rejects_duplicate_email_case_insensitively(self):
        User.objects.create_user(
            email='user@example.com',
            password='StrongPassword_123!',
        )

        response = self.client.post(
            self.register_url,
            {
                'email': 'USER@example.com',
                'password': 'StrongPassword_123!',
                'personal_data_consent': True,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 1)

    def test_verifies_email_with_valid_token(self):
        user = User.objects.create_user(
            email='user@example.com',
            password='StrongPassword_123!',
        )
        token = create_email_verification_token(user)

        response = self.client.post(
            self.verify_email_url,
            {'token': token},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_rejects_invalid_verification_token(self):
        response = self.client.post(
            self.verify_email_url,
            {'token': 'invalid-token'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    @patch('accounts.services.registration.schedule_verification_email')
    def test_resends_verification_without_disclosing_account(self, schedule_email):
        response = self.client.post(
            self.resend_url,
            {'email': 'missing@example.com'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        schedule_email.assert_not_called()

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        FRONTEND_URL='https://promo.example.com',
    )
    def test_verification_email_contains_signed_link(self):
        user = User.objects.create_user(
            email='user@example.com',
            password='StrongPassword_123!',
        )

        send_verification_email(user.pk)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('https://promo.example.com/verify-email?', mail.outbox[0].body)


class JwtAuthApiTests(TestCase):
    login_url = reverse('auth-login')
    refresh_url = reverse('auth-refresh')
    logout_url = reverse('auth-logout')

    def create_user(self, *, is_email_verified=True):
        user = User.objects.create_user(
            email='user@example.com',
            password='StrongPassword_123!',
            is_email_verified=is_email_verified,
        )
        Profile.objects.create(user=user)
        return user

    def login(self, **overrides):
        data = {
            'email': 'user@example.com',
            'password': 'StrongPassword_123!',
        }
        data.update(overrides)
        return self.client.post(
            self.login_url,
            data,
            content_type='application/json',
        )

    def test_login_returns_token_pair(self):
        user = self.create_user()

        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())
        self.assertIn('refresh', response.json())
        user.refresh_from_db()
        self.assertIsNotNone(user.last_login)

    def test_login_rejects_invalid_credentials(self):
        self.create_user()

        response = self.login(password='wrong-password')

        self.assertEqual(response.status_code, 400)
        self.assertNotIn('access', response.json())

    def test_login_requires_verified_email(self):
        self.create_user(is_email_verified=False)

        response = self.login()

        self.assertEqual(response.status_code, 400)
        self.assertNotIn('access', response.json())

    def test_refresh_rotates_token_and_logout_blacklists_it(self):
        self.create_user()
        login_response = self.login()
        refresh = login_response.json()['refresh']

        refresh_response = self.client.post(
            self.refresh_url,
            {'refresh': refresh},
            content_type='application/json',
        )

        self.assertEqual(refresh_response.status_code, 200)
        rotated_refresh = refresh_response.json()['refresh']
        logout_response = self.client.post(
            self.logout_url,
            {'refresh': rotated_refresh},
            content_type='application/json',
        )
        self.assertEqual(logout_response.status_code, 204)

        reused_response = self.client.post(
            self.refresh_url,
            {'refresh': rotated_refresh},
            content_type='application/json',
        )
        self.assertEqual(reused_response.status_code, 400)

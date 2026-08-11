from django.test import TestCase
from django.urls import reverse

from .models import User


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

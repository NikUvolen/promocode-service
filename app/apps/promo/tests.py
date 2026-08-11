from django.test import TestCase
from django.urls import reverse

from accounts.models import User


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

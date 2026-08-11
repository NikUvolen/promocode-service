from django.test import TestCase
from django.urls import reverse


class ApiDocumentationTests(TestCase):
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
        )
        for path in expected_paths:
            with self.subTest(path=path):
                self.assertIn(path, schema['paths'])

    def test_swagger_ui_renders(self):
        response = self.client.get(reverse('swagger-ui'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="swagger-ui"')

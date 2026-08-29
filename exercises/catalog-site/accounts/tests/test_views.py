from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class SignUpViewTests(TestCase):
    def test_valid_signup_creates_user_and_redirects_to_login(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "new-user",
                "email": "new@example.com",
                "password1": "strong-test-password-123",
                "password2": "strong-test-password-123",
            },
        )
        self.assertRedirects(response, reverse("login"))
        self.assertTrue(get_user_model().objects.filter(username="new-user").exists())

    def test_duplicate_email_is_rejected(self):
        get_user_model().objects.create_user(
            username="existing",
            email="existing@example.com",
            password="strong-test-password-123",
        )
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "another",
                "email": "existing@example.com",
                "password1": "strong-test-password-123",
                "password2": "strong-test-password-123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(get_user_model().objects.count(), 1)

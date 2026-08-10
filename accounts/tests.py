from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.models import UserProfile

User = get_user_model()

class AccountsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='Password123!',
            first_name='Kwame',
            last_name='Mensah'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            role='ADMIN',
            phone_number='0241234567'
        )

    def test_user_profile_creation(self):
        self.assertEqual(self.user.profile.role, 'ADMIN')
        self.assertEqual(str(self.user.profile), "testuser (Administrator)")

    def test_login_success(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'testuser@example.com',
            'password': 'Password123!'
        })
        self.assertRedirects(response, reverse('dashboard:dashboard'))

    def test_login_failure(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'testuser@example.com',
            'password': 'WrongPassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username/email or password.")

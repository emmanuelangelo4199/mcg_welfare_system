from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import SystemSetting, AuditLog

User = get_user_model()


class SystemSettingsTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin', password='admin-password')

    def test_settings_page_requires_authentication(self):
        response = self.client.get(reverse('core:system_settings'))
        self.assertRedirects(response, reverse('accounts:login'))

    def test_settings_page_blocked_for_users_without_a_role(self):
        user = User.objects.create_user(username='plain', password='password')
        self.client.force_login(user)
        response = self.client.get(reverse('core:system_settings'))
        self.assertRedirects(response, reverse('dashboard:dashboard'))

    def test_settings_page_renders_defaults(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('core:system_settings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="SOCIETY_NAME"')
        self.assertContains(response, 'value="5000.00"')
        self.assertContains(response, 'value="90"')

    def test_society_section_saves_settings_and_writes_audit_log(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('core:system_settings'), {
            'section': 'society_profile',
            'SOCIETY_NAME': 'Wesley Methodist Church',
            'SOCIETY_DESCRIPTION': 'Abossey Okai Circuit - Accra Diocese',
            'SOCIETY_ADDRESS': 'P.O. Box 45, Accra',
            'SOCIETY_EMAIL': 'wesley@example.org',
            'SOCIETY_PHONE': '+233 24 456 7890',
        })

        self.assertRedirects(response, f"{reverse('core:system_settings')}?tab=society-profile")
        self.assertEqual(SystemSetting.objects.get(key='SOCIETY_NAME').value, 'Wesley Methodist Church')
        self.assertEqual(SystemSetting.objects.get(key='SOCIETY_EMAIL').description, 'Society email address')
        self.assertTrue(
            AuditLog.objects.filter(
                user=self.admin,
                model_name='SystemSetting',
                action__contains='Society profile',
            ).exists()
        )

    def test_financial_section_validates_numbers(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('core:system_settings'), {
            'section': 'financial',
            'TREASURER_APPROVAL_LIMIT': 'not-a-number',
            'FINANCE_COMMITTEE_THRESHOLD': '15000',
            'DIOCESE_ASSESSMENT_RATE': '150',
            'CONNEXION_QUOTA_RATE': '15',
            'CIRCUIT_SUPPORT_RATE': '5',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter a valid number.')
        self.assertContains(response, 'between 0 and 100')
        self.assertFalse(SystemSetting.objects.filter(key='TREASURER_APPROVAL_LIMIT').exists())

    def test_security_section_stores_toggles(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('core:system_settings'), {
            'section': 'security',
            'SESSION_TIMEOUT_MINUTES': '45',
            'PASSWORD_EXPIRY_DAYS': '60',
            'MFA_REQUIRED': 'on',
            # HIGH_RISK_CONFIRMATION left off
        })

        self.assertEqual(SystemSetting.objects.get(key='SESSION_TIMEOUT_MINUTES').value, '45')
        self.assertEqual(SystemSetting.objects.get(key='MFA_REQUIRED').value, 'TRUE')
        self.assertEqual(SystemSetting.objects.get(key='HIGH_RISK_CONFIRMATION').value, 'FALSE')

    def test_unknown_section_is_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('core:system_settings'), {'section': 'bogus'})
        self.assertRedirects(response, reverse('core:system_settings'))
        self.assertEqual(SystemSetting.objects.count(), 0)

    def test_tab_parameter_selects_the_active_panel(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('core:system_settings'), {'tab': 'financial-config'})
        self.assertContains(response, 'data-initial-tab="financial-config"')
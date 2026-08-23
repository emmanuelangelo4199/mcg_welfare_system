from decimal import Decimal
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from finance.models import Budget, ExpenseLedger
from notifications.models import SystemNotification

User = get_user_model()


class TreasurerBudgetPanelTests(TestCase):
    """The budget utilisation panel joins Budget to ExpenseLedger on the shared
    category keys, and only counts approved spend from the same fiscal year."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='treasurer', email='t@example.com', password='Password123!')
        UserProfile.objects.create(user=self.user, role='TREASURER')
        self.client.login(username='treasurer', password='Password123!')
        self.today = timezone.localdate()

    def test_budget_panel_counts_matching_spend(self):
        Budget.objects.create(
            fiscal_year=self.today.year, category='UTILITIES',
            allocated_amount=Decimal('2500.00'))
        ExpenseLedger.objects.create(
            title='Electricity', category='UTILITIES', amount=Decimal('2150.00'),
            date=self.today, status='APPROVED')
        ExpenseLedger.objects.create(
            title='Fuel', category='TRANSPORT', amount=Decimal('900.00'),
            date=self.today, status='APPROVED')

        response = self.client.get(reverse('dashboard:treasurer_dashboard'))
        rows = {row['category']: row for row in response.context['budgets']}

        utilities = rows['Utility Bills (Water/Electricity)']
        self.assertEqual(utilities['spent'], Decimal('2150.00'))
        self.assertEqual(utilities['raw_share'], 86)
        self.assertEqual(utilities['state'], 'warning')

    def test_unapproved_and_other_year_spend_is_excluded(self):
        Budget.objects.create(
            fiscal_year=self.today.year, category='WELFARE',
            allocated_amount=Decimal('1000.00'))
        ExpenseLedger.objects.create(
            title='Pending parcel', category='WELFARE', amount=Decimal('400.00'),
            date=self.today, status='PENDING')
        ExpenseLedger.objects.create(
            title='Last year', category='WELFARE', amount=Decimal('700.00'),
            date=datetime.date(self.today.year - 1, 6, 1), status='APPROVED')

        response = self.client.get(reverse('dashboard:treasurer_dashboard'))
        welfare = response.context['budgets'][0]
        self.assertEqual(welfare['spent'], 0)


class MainDashboardTopbarTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='steward', first_name='Ama', last_name='Boateng',
            email='ama@example.com', password='Password123!')
        UserProfile.objects.create(user=self.user, role='SOCIETY_STEWARD')
        self.client.login(username='steward', password='Password123!')

    def test_topbar_renders_identity_and_search(self):
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Society Portal')
        self.assertContains(response, 'Search members')
        self.assertContains(response, 'Ama Boateng')
        self.assertEqual(response.context['user_initials'], 'AB')
        self.assertEqual(response.context['unread_notification_count'], 0)

    def test_topbar_shows_unread_notification_badge(self):
        SystemNotification.objects.create(
            user=self.user, title='Pending approval', message='A case needs review')
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.context['unread_notification_count'], 1)
        self.assertContains(response, '1 unread')
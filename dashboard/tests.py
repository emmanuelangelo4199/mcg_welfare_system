from decimal import Decimal
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from finance.models import Budget, ExpenseLedger

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
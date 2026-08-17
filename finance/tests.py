import datetime
from decimal import Decimal
from importlib import import_module

from django.apps import apps
from django.utils.html import escape
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from finance.models import EXPENSE_CATEGORY_CHOICES, Budget, ExpenseLedger

User = get_user_model()


class ExpenseCategoryTests(TestCase):
    """Budget utilisation relies on Budget.category and ExpenseLedger.category
    agreeing, so both sides must use the same keys."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='treasurer', email='t@example.com', password='Password123!')
        UserProfile.objects.create(user=self.user, role='TREASURER')
        self.client.login(username='treasurer', password='Password123!')
        self.today = timezone.localdate()

    def test_both_models_share_one_choice_list(self):
        self.assertEqual(ExpenseLedger.CATEGORY_CHOICES, EXPENSE_CATEGORY_CHOICES)
        self.assertEqual(Budget.CATEGORY_CHOICES, EXPENSE_CATEGORY_CHOICES)

    def test_expense_and_budget_forms_offer_identical_options(self):
        expense_page = self.client.get(reverse('finance:record_expense'))
        budget_page = self.client.get(reverse('finance:budget_manage'))

        for value, label in EXPENSE_CATEGORY_CHOICES:
            self.assertContains(expense_page, f'value="{value}"')
            self.assertContains(budget_page, f'value="{value}"')
            self.assertContains(budget_page, escape(label))

    def test_posted_expense_and_budget_categories_match(self):
        self.client.post(reverse('finance:record_expense'), {
            'title': 'Electricity bill', 'category': 'UTILITIES',
            'amount': '2150.00', 'date': str(self.today), 'description': '',
        })
        self.client.post(reverse('finance:budget_manage'), {
            'fiscal_year': self.today.year, 'category': 'UTILITIES',
            'allocated_amount': '2500.00', 'notes': '',
        })

        expense = ExpenseLedger.objects.get(title='Electricity bill')
        budget = Budget.objects.get(category='UTILITIES')
        self.assertEqual(expense.category, budget.category)

    def test_invalid_budget_category_is_rejected(self):
        response = self.client.post(reverse('finance:budget_manage'), {
            'fiscal_year': self.today.year, 'category': 'NOT_A_CATEGORY',
            'allocated_amount': '100.00', 'notes': '',
        }, follow=True)

        self.assertEqual(Budget.objects.count(), 0)
        self.assertContains(response, 'valid budget category')

    def test_resetting_a_budget_updates_instead_of_duplicating(self):
        payload = {'fiscal_year': self.today.year, 'category': 'ADMIN', 'notes': ''}
        self.client.post(reverse('finance:budget_manage'), {**payload, 'allocated_amount': '500.00'})
        self.client.post(reverse('finance:budget_manage'), {**payload, 'allocated_amount': '750.00'})

        self.assertEqual(Budget.objects.filter(category='ADMIN').count(), 1)
        self.assertEqual(Budget.objects.get(category='ADMIN').allocated_amount, Decimal('750.00'))

    def test_unknown_posted_category_falls_back_to_other(self):
        self.client.post(reverse('finance:record_expense'), {
            'title': 'Mystery spend', 'category': 'made up',
            'amount': '10.00', 'date': str(self.today), 'description': '',
        })
        self.assertEqual(ExpenseLedger.objects.get(title='Mystery spend').category, 'OTHER')


class LegacyCategoryMigrationTests(TestCase):
    """The 0002 data migration converts pre-existing free text without losing it."""

    def setUp(self):
        migration = import_module('finance.migrations.0002_expense_category_choices')
        self.normalise = migration.normalise
        self.today = timezone.localdate()

    def test_known_free_text_is_mapped_to_keys(self):
        ExpenseLedger.objects.create(
            title='Bill', category='Utilities', amount=Decimal('1.00'), date=self.today)
        Budget.objects.create(
            fiscal_year=self.today.year, category='Welfare Support',
            allocated_amount=Decimal('1.00'))

        self.normalise(apps, None)

        self.assertEqual(ExpenseLedger.objects.get(title='Bill').category, 'UTILITIES')
        self.assertEqual(Budget.objects.first().category, 'WELFARE')

    def test_budget_and_expense_wording_converge(self):
        """'Welfare Support' (budget) and 'Welfare' (expense) never matched before."""
        ExpenseLedger.objects.create(
            title='Parcels', category='Welfare', amount=Decimal('1.00'), date=self.today)
        Budget.objects.create(
            fiscal_year=self.today.year, category='Welfare Support',
            allocated_amount=Decimal('1.00'))

        self.normalise(apps, None)

        self.assertEqual(
            ExpenseLedger.objects.get(title='Parcels').category,
            Budget.objects.first().category,
        )

    def test_unrecognised_text_is_preserved_in_a_note(self):
        ExpenseLedger.objects.create(
            title='Odd one', category='Bouncy castle hire',
            amount=Decimal('1.00'), date=self.today, description='Original note')

        self.normalise(apps, None)

        expense = ExpenseLedger.objects.get(title='Odd one')
        self.assertEqual(expense.category, 'OTHER')
        self.assertIn('Original note', expense.description)
        self.assertIn('Bouncy castle hire', expense.description)

    def test_already_migrated_rows_are_left_alone(self):
        ExpenseLedger.objects.create(
            title='Done', category='TRANSPORT', amount=Decimal('1.00'),
            date=self.today, description='untouched')

        self.normalise(apps, None)

        expense = ExpenseLedger.objects.get(title='Done')
        self.assertEqual(expense.category, 'TRANSPORT')
        self.assertEqual(expense.description, 'untouched')
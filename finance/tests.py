from django.test import TestCase
from finance.models import IncomeLedger, ExpenseLedger

class FinanceTestCase(TestCase):
    def setUp(self):
        self.income = IncomeLedger.objects.create(
            category='TITHE',
            amount=5000.00,
            date='2026-08-10'
        )
        self.expense = ExpenseLedger.objects.create(
            title='Utility Bills',
            category='Utilities',
            amount=800.00,
            date='2026-08-10',
            status='PENDING'
        )

    def test_income_entry(self):
        self.assertEqual(self.income.amount, 5000.00)

    def test_expense_approval(self):
        self.assertEqual(self.expense.status, 'PENDING')
        self.expense.status = 'APPROVED'
        self.expense.save()
        self.assertEqual(self.expense.status, 'APPROVED')

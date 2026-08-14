from django.test import TestCase
from members.models import Member
from welfare_cases.models import WelfareCase, WelfareDisbursement

class WelfareCasesTestCase(TestCase):
    def setUp(self):
        self.member = Member.objects.create(
            first_name='Abena',
            last_name='Osei',
            gender='F',
            status='ACTIVE'
        )
        self.wcase = WelfareCase.objects.create(
            member=self.member,
            case_type='MEDICAL',
            title='Hospital Admission Support',
            description='Emergency medical bill assistance',
            requested_amount=1500.00 
        )

    def test_welfare_case_creation(self):
        self.assertEqual(self.wcase.status, 'SUBMITTED')
        self.assertEqual(self.wcase.requested_amount, 1500.00)

    def test_disbursement(self):
        disbursement = WelfareDisbursement.objects.create(
            welfare_case=self.wcase,
            amount=1200.00,
            disbursement_date='2026-08-10',
            payment_method='Mobile Money'
        )
        self.wcase.status = 'DISBURSED'
        self.wcase.approved_amount = 1200.00
        self.wcase.save()

        self.assertEqual(self.wcase.status, 'DISBURSED')
        self.assertEqual(disbursement.amount, 1200.00)
